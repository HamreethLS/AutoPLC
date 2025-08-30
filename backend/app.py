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
from backend.agents.knowledge_agent import create_knowledge_agent
from backend.agents.retrieval_agent import create_retrieval_agent # <-- IMPORT NEW AGENT
from backend.tools.compiler import run_iec2c_compiler
from backend.tools.knowledge_base import query_knowledge_base
from backend.tools.retrieval_tools import search_tavily, search_mouser # <-- IMPORT NEW TOOLS

# --- 1. INITIALIZATION ---
load_dotenv()

# --- ROBUST FLASK APP INITIALIZATION ---
basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'))

# --- HELPER FUNCTION ---
def extract_code_block(text: str) -> str:
    """Extracts a Structured Text code block from a string."""
    pattern = r"```(?:st|iec|structuredtext|structured text|iec6113-3)?\n?(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    program_match = re.search(r"PROGRAM.*END_PROGRAM", text, re.DOTALL | re.IGNORECASE)
    if program_match:
        return program_match.group(0).strip()
    return text

# --- 2. CONFIGURE APIs ---
nim_api_key = os.getenv("NVIDIA_API_KEY")
if not nim_api_key:
    raise ValueError("NVIDIA_API_KEY not found in .env file.")
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not found in .env file.")

# --- MODEL CONFIGURATIONS ---
llm_config_gemini = {
    "config_list": [{"model": "gemini-1.5-pro-latest", "api_key": google_api_key, "api_type": "google"}],
    "cache_seed": 42,
}
llm_config_coder = {
    "config_list": [{"model": "meta/llama-3.1-70b-instruct", "api_key": nim_api_key, "base_url": "https://integrate.api.nvidia.com/v1", "api_type": "openai"}],
    "cache_seed": 42,
}
llm_config_tool_user = {
    "config_list": [{"model": "nvidia/llama-3.3-nemotron-super-49b-v1.5", "api_key": nim_api_key, "base_url": "https://integrate.api.nvidia.com/v1", "api_type": "openai"}],
    "cache_seed": 42,
}

# --- 3. SETUP AUTOGEN WORKFLOW ---
planner = create_planner_agent(llm_config_gemini)
coder = create_coder_agent(llm_config_coder)

# Agents that use tools will use the powerful Nemotron model
validator = create_validator_agent(llm_config_tool_user)
knowledge_agent = create_knowledge_agent(llm_config_tool_user)
retrieval_agent = create_retrieval_agent(llm_config_tool_user) 

# User Proxy with all tools mapped
user_proxy = autogen.UserProxyAgent(
    name="UserProxy",
    human_input_mode="NEVER",
    code_execution_config=False, 
    function_map={
        "run_iec2c_compiler": run_iec2c_compiler,
        "query_knowledge_base": query_knowledge_base,
        "search_tavily": search_tavily,
        "search_mouser": search_mouser,
    }
)

# Add the new agent to the group chat
groupchat = autogen.GroupChat(
    agents=[user_proxy, planner, knowledge_agent, retrieval_agent, coder, validator], 
    messages=[], 
    max_round=20 # Increased max rounds for more complex conversation
)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config_gemini)

# --- 4. FLASK ROUTES ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        if not prompt: return jsonify({"error": "Prompt is missing"}), 400
        
        user_proxy.reset(); manager.reset()
        
        initial_message = f"""The user wants to generate Structured Text code for the following task: '{prompt}'.
        
        The Planner must start by consulting the KnowledgeAgent for basic rules, and then the RetrievalAgent for any specific hardware details mentioned in the prompt."""
        
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
