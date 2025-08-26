import os
import autogen
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
import requests 

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
# Official Gemini config for the Planner
llm_config_planner = {
    "config_list": [
        {
            "model": "gemini-1.5-pro-latest", 
            "api_key": google_api_key,
            "api_type": "google" # Specify the API type for AutoGen's built-in client
        }
    ],
    "cache_seed": 42,
}

# NVIDIA NIM config for the Coder and Validator
llm_config_nim = {
    "config_list": [
        {
            "model": "meta/llama-3.1-70b-instruct",
            "api_key": nim_api_key,
            "base_url": "https://integrate.api.nvidia.com/v1"
        }
    ],
    "cache_seed": 42,
}


# --- 3. SETUP AUTOGEN WORKFLOW ---
planner = create_planner_agent(llm_config_planner)
coder = create_coder_agent(llm_config_nim)
llm_config_validator = llm_config_nim.copy()
llm_config_validator["tools"] = [{"type": "function","function": {"name": "run_iec2c_compiler","description": "Compiles Structured Text code.","parameters": {"type": "object","properties": {"code": {"type": "string"}},"required": ["code"],},},}]
validator = create_validator_agent(llm_config_validator)

user_proxy = autogen.UserProxyAgent(name="UserProxy",human_input_mode="NEVER",code_execution_config={"executor": autogen.coding.LocalCommandLineCodeExecutor(work_dir="coding")},function_map={"run_iec2c_compiler": run_iec2c_compiler})
groupchat = autogen.GroupChat(agents=[user_proxy, planner, coder, validator], messages=[], max_round=12)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config_nim)


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
        First, the Planner will create a plan.
        Next, the Coder will write the code based on the plan.
        Finally, the Validator will use the 'run_iec2c_compiler' tool to check the code. The UserProxy will execute this tool call."""
        user_proxy.initiate_chat(manager, message=initial_message)
        chat_history = user_proxy.chat_messages[manager]
        best_code = "No code was generated."; final_validation_message = "No validation was performed."; success = False
        for i, msg in enumerate(chat_history):
            if msg.get('name') == 'Coder' and msg.get('content'):
                for next_msg in chat_history[i+1:]:
                    if next_msg.get('role') == 'tool':
                        validation_result = next_msg.get('content', '')
                        if "Compilation Successful." in validation_result:
                            best_code = msg['content'].strip(); final_validation_message = validation_result; success = True; break
                        break 
            if success: break
        if not success:
            for msg in reversed(chat_history):
                if msg.get('name') == 'Coder' and msg.get('content'): best_code = msg['content'].strip(); break
            for msg in reversed(chat_history):
                if msg.get('role') == 'tool': final_validation_message = msg['content'].strip(); break
        formatted_history = []
        for msg in chat_history:
            role = msg.get('name', msg.get('role')); content = msg.get('content')
            if role == 'tool': role = "UserProxy (Tool Result)"
            if not role or not content: continue
            if "tool_calls" in msg: continue
            formatted_history.append({"role": role, "content": content})
        return jsonify({"success": success, "generated_code": best_code, "final_validation_message": final_validation_message, "history": formatted_history})
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": str(e)}), 500

# --- 5. GEMINI API ROUTES (Unchanged) ---
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
