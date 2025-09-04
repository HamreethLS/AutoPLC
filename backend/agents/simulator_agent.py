import os
import requests
import json
import time

class SimulatorAgent:
    """Simulator Agent - integrates with OpenPLC runtime and ScadaBR HMI"""
    def __init__(self):
        self.openplc_url = os.getenv("OPENPLC_URL", "http://localhost:8080")
        self.scadabr_url = os.getenv("SCADABR_URL", "http://localhost:9090")
        self.temp_dir = os.path.join(os.getcwd(), "temp")
        os.makedirs(self.temp_dir, exist_ok=True)

    def save_code_to_file(self, code: str) -> str:
        filename = f"plc_program_{int(time.time())}.st"
        filepath = os.path.join(self.temp_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        return filepath

    def upload_to_openplc(self, st_file_path: str) -> dict:
        try:
            url = f"{self.openplc_url}/programs"
            with open(st_file_path, "rb") as f:
                files = {'file': (os.path.basename(st_file_path), f, 'text/plain')}
                r = requests.post(url, files=files, timeout=30)
                return {"success": r.status_code == 200, "msg": r.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_plc_simulation(self) -> dict:
        try:
            r = requests.post(f"{self.openplc_url}/start", timeout=10)
            return {"success": r.status_code == 200, "msg": r.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_plc_simulation(self) -> dict:
        try:
            r = requests.post(f"{self.openplc_url}/stop", timeout=10)
            return {"success": r.status_code == 200, "msg": r.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_plc_status(self) -> dict:
        try:
            r = requests.get(f"{self.openplc_url}/status", timeout=10)
            return {"success": True, "status": r.text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_variable_values(self) -> dict:
        try:
            r = requests.get(f"{self.openplc_url}/monitoring", timeout=10)
            return {"success": True, "vars": r.text}
        except Exception as e:
            return {"success": False, "error": str(e)}
