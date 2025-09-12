"""
Simulator Agent - integrates with the OpenPLC runtime.
"""

import os
import requests
import json
import time
import re

from backend.utils.nim_client import enhanced_nim_client
from typing import Dict

class SimulatorAgent:
    """Simulator Agent - integrates with the OpenPLC runtime."""
    def __init__(self):
        self.openplc_url = os.getenv("OPENPLC_URL", "http://localhost:8080")
        # ScadaBR integration is planned for a future version
        self.scadabr_url = os.getenv("SCADABR_URL", "http://localhost:9090")
        self.temp_dir = os.path.join(os.getcwd(), "temp")
        os.makedirs(self.temp_dir, exist_ok=True)

    def save_code_to_file(self, code: str) -> str:
        """Saves the generated Structured Text code to a temporary file."""
        filename = f"plc_program_{int(time.time())}.st"
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        return filepath

    def upload_to_openplc(self, st_file_path: str) -> dict:
        """Uploads a .st file to the OpenPLC runtime."""
        try:
            url = f"{self.openplc_url}/programs"
            with open(st_file_path, "rb") as f:
                files = {'file': (os.path.basename(st_file_path), f, 'text/plain')}
                r = requests.post(url, files=files, timeout=30)
                r.raise_for_status()
                return {"success": True, "message": r.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_plc_simulation(self) -> dict:
        """Sends a command to start the PLC simulation."""
        try:
            r = requests.post(f"{self.openplc_url}/start", timeout=10)
            r.raise_for_status()
            return {"success": True, "message": r.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_plc_simulation(self) -> dict:
        """Sends a command to stop the PLC simulation."""
        try:
            r = requests.post(f"{self.openplc_url}/stop", timeout=10)
            r.raise_for_status()
            return {"success": True, "message": r.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_plc_status(self) -> dict:
        """Retrieves the current status from the OpenPLC runtime."""
        try:
            r = requests.get(f"{self.openplc_url}/status", timeout=10)
            r.raise_for_status()
            return {"success": True, "status": r.json() if r.text else "Unknown"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_variable_values(self) -> dict:
        """Retrieves live variable values from the OpenPLC runtime."""
        try:
            r = requests.get(f"{self.openplc_url}/monitoring", timeout=10)
            r.raise_for_status()
            return {"success": True, "variables": r.json() if r.text else {}}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def generate_dashboard_definition(self, code: str, prompt: str) -> Dict:
        """Uses an LLM to generate a JSON definition for a dynamic simulation dashboard."""
        
        dashboard_prompt = f"""
You are a UI/UX expert for industrial automation dashboards. Your task is to create a JSON definition for a web-based simulator UI based on the provided Structured Text (ST) code and the original user prompt.

**User's Original Prompt:**
---
{prompt}
---

**Generated ST Code:**
---
```st
{code}
```
---

**Instructions:**
1.  Analyze the code to identify all input and output variables (e.g., `StartButton AT %I0.0`, `MotorCoil AT %Q0.0`).
2.  Based on the user's prompt and variable names, infer the best UI component for each variable.
    - For inputs that act like buttons (e.g., 'Start', 'Stop', 'Reset'), use a `"momentary_button"`.
    - For inputs that act like switches (e.g., 'Enable', 'AutoMode'), use a `"toggle_switch"`.
    - For outputs, use an `"indicator_light"` for booleans or a `"display_value"` for numeric types.
3.  Organize the components into logical groups: `"inputs"` and `"outputs"`.
4.  Provide a suitable title for the dashboard.
5.  Output a single, valid JSON object with the following structure. Do not include any other text or markdown formatting.

**JSON Output Format:**
{{
  "title": "A descriptive title for the simulation",
  "layout": {{
    "groups": [
      {{"id": "inputs", "title": "Inputs"}},
      {{"id": "outputs", "title": "Outputs"}}
    ]
  }},
  "components": [
    {{
      "id": "unique_component_id",
      "type": "momentary_button" | "toggle_switch" | "indicator_light" | "display_value",
      "label": "User-friendly label (e.g., 'Start Button')",
      "variable": "Exact_Variable_Name_From_Code",
      "group": "inputs" | "outputs"
    }}
  ]
}}
"""
        try:
            response_str = await enhanced_nim_client.call_agent_simple(
                agent_role="validator", # The validator model is good at structured output
                prompt=dashboard_prompt,
                temperature=0.1,
                max_tokens=1024
            )
            
            # Clean and parse the JSON
            json_match = re.search(r'\{.*\}', response_str, re.DOTALL)
            if not json_match:
                raise json.JSONDecodeError("No JSON object found in LLM response.", response_str, 0)
            
            dashboard_def = json.loads(json_match.group(0))
            return {"success": True, "dashboard": dashboard_def}

        except json.JSONDecodeError as e:
            return {"success": False, "error": f"LLM returned invalid JSON for dashboard: {e}. Response: {response_str}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to generate dashboard definition: {e}"}