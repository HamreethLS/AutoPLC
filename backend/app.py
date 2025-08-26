import os
import autogen
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests
import re

# Import agent and tool creation functions 
from backend.agents.planner_agent import create_planner_agent
from backend.agents.coder_agent import create_coder_agent
from backend.agents.validator_agent import create_validator_agent
from backend.tools.compiler import run_iec2c_compiler

# --- 1. INITIALIZATION ---
load_dotenv()

# --- ROBUST FLASK APP INITIALIZATION ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'))

# --- HELPER FUNCTION ---
def extract_code_block(text: str) -> str:
    """Extracts a Structured Text code block from a string, cleaning up common LLM artifacts."""
    # Clean up stdout/stdin tags that the model might add
    text = re.sub(r'\[/?stdout\]', '', text, flags=re.IGNORECASE).strip()
    
    # Pattern to match ```...```, with an optional language identifier
    pattern = r"```(?:st|iec|structuredtext|iec6113-3)?\n?(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Fallback for code that isn't in a markdown block but is a valid program
    program_match = re.search(r"PROGRAM.*END_PROGRAM", text, re.DOTALL | re.IGNORECASE)
    if program_match:
        return program_match.group(0).strip()
        
    return text # Last resort fallback

# --- 2. CONFIGURE APIs ---
# NVIDIA NIM API Key
nim_api_key = os.getenv("NVIDIA_API_KEY")
if not nim_api_key:
    raise ValueError("NVIDIA_API_KEY not found in .env file.")

# Google Gemini API Key
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file.")

# --- MODEL CONFIGURATIONS ---
# Gemini config for the Planner and GroupChat Manager
llm_config_gemini = {
    "config_list": [
        {
            "model": "gemini-1.5-pro-latest", 
            "api_key": google_api_key,
            "api_type": "google"
        }
    ],
    "cache_seed": 42,
}

# NVIDIA NIM config for the Coder (Llama 3.1)
llm_config_coder = {
    "config_list": [
        {
            "model": "meta/llama-3.1-70b-instruct",
            "api_key": nim_api_key,
            "base_url": "https://integrate.api.nvidia.com/v1",
            "api_type": "openai"
        }
    ],
    "cache_seed": 42,
}

# NVIDIA NIM config for the Validator (Nemotron-4 49B) - FINAL & VERIFIED
llm_config_validator_base = {
    "config_list": [
        {
            "model": "nvidia/llama-3.3-nemotron-super-49b-v1.5",
            "api_key": nim_api_key,
            "base_url": "https://integrate.api.nvidia.com/v1",
            "api_type": "openai"
        }
    ],
    "cache_seed": 42,
}


# --- 3. SETUP AUTOGEN WORKFLOW ---
planner = create_planner_agent(llm_config_gemini)      # Planner uses Gemini
coder = create_coder_agent(llm_config_coder)           # Coder uses Llama 3.1

# Create a dedicated, tool-enabled config for the Validator using Nemotron
llm_config_validator = llm_config_validator_base.copy()
llm_config_validator["tools"] = [{"type": "function","function": {"name": "run_iec2c_compiler","description": "Compiles Structured Text code.","parameters": {"type": "object","properties": {"code": {"type": "string"}},"required": ["code"],},},}]
validator = create_validator_agent(llm_config_validator) # Validator now uses Nemotron

user_proxy = autogen.UserProxyAgent(
    name="UserProxy",
    human_input_mode="NEVER",
    code_execution_config=False, 
    function_map={"run_iec2c_compiler": run_iec2c_compiler}
)

groupchat = autogen.GroupChat(agents=[user_proxy, planner, coder, validator], messages=[], max_round=12)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config_gemini) # Manager uses Gemini for orchestration


# --- 4. FLASK ROUTES ---
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """Handles the code generation request from the frontend."""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        if not prompt: return jsonify({"error": "Prompt is missing"}), 400
        
        user_proxy.reset(); manager.reset()
        
        initial_message = f"""The user wants to generate Structured Text code for the following task: '{prompt}'.
        This original request should be used by the Validator for semantic analysis.
        
        Workflow:
        1. The Planner will create a plan.
        2. The Coder will write the code based on the plan.
        3. The Validator will use the 'run_iec2c_compiler' tool for a syntax check AND perform a semantic check against the original request.
        4. The UserProxy will execute the compiler tool call."""
        
        user_proxy.initiate_chat(manager, message=initial_message)
        chat_history = user_proxy.chat_messages[manager]
        
        successful_codes = []
        for i, msg in enumerate(chat_history):
            if msg.get('role') == 'tool' and "Compilation Successful." in msg.get('content', ''):
                for j in range(i - 1, -1, -1):
                    prev_msg = chat_history[j]
                    if prev_msg.get('name') == 'Coder' and prev_msg.get('content'):
                        code = extract_code_block(prev_msg.get('content'))
                        if code and "BEGIN" in code and "END_PROGRAM" in code:
                            successful_codes.append(code)
                        break

        best_code = "No valid, compiled code was generated."
        final_validation_message = "Validation failed to produce a usable program."
        success = False

        if successful_codes:
            success = True
            best_code = max(successful_codes, key=len)
            final_validation_message = "Compilation Successful. The most complete, valid version was selected."
        else:
            for msg in reversed(chat_history):
                if msg.get('name') == 'Coder' and msg.get('content'):
                    best_code = extract_code_block(msg.get('content'))
                    break
            for msg in reversed(chat_history):
                if msg.get('role') == 'tool':
                    final_validation_message = msg.get('content', '').strip()
                    break

        formatted_history = []
        for msg in chat_history:
            role = msg.get('name', msg.get('role')); content = msg.get('content')
            if role == 'tool': role = "UserProxy (Tool Result)"
            if not role or not content: continue
            if "tool_calls" in msg: continue
            formatted_history.append({"role": role, "content": content})
            
        return jsonify({
            "success": success, 
            "generated_code": best_code, 
            "final_validation_message": final_validation_message, 
            "history": formatted_history
        })
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500

# --- 5. GEMINI API ROUTES ---
def call_gemini_api(prompt):
    gemini_api_key = os.getenv("GOOGLE_API_KEY", "") 
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={gemini_api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(api_url, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        result = response.json()
        if (result.get('candidates') and result['candidates'][0].get('content') and 
            result['candidates'][0]['content'].get('parts') and result['candidates'][0]['content']['parts'][0].get('text')):
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            return "Could not extract a valid response from the Gemini API."
    except requests.exceptions.RequestException as e:
        return f"Error connecting to the Gemini API: {e}"

@app.route('/explain', methods=['POST'])
def explain_code():
    data = request.get_json(); code = data.get('code')
    if not code: return jsonify({"error": "Code is missing"}), 400
    prompt = f"Explain this ST code:\n```st\n{code}\n```"
    explanation = call_gemini_api(prompt)
    return jsonify({"content": explanation})

@app.route('/improve', methods=['POST'])
def improve_code():
    data = request.get_json(); code = data.get('code')
    if not code: return jsonify({"error": "Code is missing"}), 400
    prompt = f"Suggest improvements for this ST code:\n```st\n{code}\n```"
    suggestions = call_gemini_api(prompt)
    return jsonify({"content": suggestions})

# --- 6. RUN THE APPLICATION ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)
