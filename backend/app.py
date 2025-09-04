import os
import re
import uuid
import threading
import time
import autogen

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from backend.agents.planner_agent import create_planner_agent
from backend.agents.coder_agent import create_coder_agent
from backend.agents.validator_agent import create_validator_agent
from backend.agents.knowledge_agent import create_knowledge_agent
from backend.tools.compiler import run_iec2c_compiler
from backend.tools.knowledge_base import query_knowledge_base, initialize_knowledge_base
from backend.tools.linter import run_linter

load_dotenv()
app = Flask(__name__)
CORS(app)
tasks = {}
active_threads = {}

def extract_code_block(text: str) -> str:
    text = text.replace('\r\n', '\n').strip()
    pattern = r"``````"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    if matches:
        return max(matches, key=len).strip()
    prog = re.search(r"PROGRAM.*?END_PROGRAM", text, re.DOTALL | re.IGNORECASE)
    if prog:
        return prog.group(0).strip()
    return text

def is_placeholder(content):
    if not content: return True
    content = content.lower().strip()
    phrases = [
        "wait for my next message",
        "please wait for my next message", 
        "i will outline the plan",
        "you will receive a plan in the next message",
        "proceeding to planning phase",
        "i will create", "i'll provide more"
    ]
    return any(p in content for p in phrases)

def run_workflow(task_id, prompt):
    tasks[task_id]["status"] = "running"
    try:
        llm_config = {
            "config_list": [{
                "model": "nvidia/llama-3.1-nemotron-70b-instruct",
                "api_key": os.getenv("NVIDIA_API_KEY_1"),
                "base_url": "https://integrate.api.nvidia.com/v1",
                "api_type": "openai",
                "temperature": 0.1,
                "max_tokens": 2048
            }],
            "cache_seed": 42
        }
        # ----- AGENT SETUP -----
        planner = create_planner_agent(llm_config)
        coder = create_coder_agent(llm_config)
        validator = create_validator_agent({
            **llm_config,
            "tools": [
                {"type": "function", "function": {"name": "run_iec2c_compiler"}},
                {"type": "function", "function": {"name": "run_linter"}}
            ]
        })
        knowledge_agent = create_knowledge_agent(llm_config)

        # ---- 1. Planner: create implementation plan ----
        plan_prompt = f"Provide a detailed, complete implementation plan for this PLC system: {prompt}\nDo not say you will explain later. Output the plan now."
        planner_out = planner.generate_reply(
            messages=[{"role": "user", "content": plan_prompt}]
        )
        if is_placeholder(planner_out):
            planner_out = planner.generate_reply(
                messages=[{"role": "user", "content": plan_prompt + "\nNever say you'll provide more later."}]
            )

        # ---- 2. Coder: generate code for the plan ----
        coder_prompt = f"Generate full, working IEC 61131-3 Structured Text code for the following plan.\nPlan:\n{planner_out}\nOutput code in a single markdown code block."
        coder_out = coder.generate_reply(
            messages=[{"role": "user", "content": coder_prompt}]
        )
        code = extract_code_block(coder_out)
        if not code or not ("PROGRAM" in code and "END_PROGRAM" in code):
            code = "(* No valid code block extracted; agent response: *)\n" + coder_out

        # ---- 3. Validator: run compiler & linter ----
        compiler_result = run_iec2c_compiler(code)
        linter_result = run_linter(code)
        qscore = float("1.0" if "Compilation Successful" in compiler_result else "0.0") + \
            (1.0 if "Linter Check Passed" in linter_result else 0.5)

        # ---- 4. Record history and result ----
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["result"] = {
            "success": "Compilation Successful" in compiler_result,
            "generated_code": code,
            "quality_score": qscore,
            "compiler_result": compiler_result,
            "linter_result": linter_result,
            "generation_count": 1,
            "history": [
                {"role": "Planner", "content": planner_out},
                {"role": "Coder", "content": code},
                {"role": "Validator", "content": f"Compiler: {compiler_result}\nLinter: {linter_result}"}
            ]
        }
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)

@app.route('/api/generate', methods=['POST'])
def generate_code():
    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "pending", "result": None}
    thread = threading.Thread(target=run_workflow, args=(task_id, prompt))
    thread.daemon = True
    thread.start()
    active_threads[task_id] = thread
    return jsonify({"task_id": task_id, "status": "running"})

@app.route('/api/status/<task_id>')
def get_task_status(task_id):
    t = tasks.get(task_id)
    if not t:
        return jsonify({"error": "Task not found"}), 404
    if "error" in t:
        return jsonify({"status": t["status"], "error": t["error"]})
    if t["status"] == "completed":
        return jsonify({**t, "result": t["result"]})
    return jsonify({"status": t["status"]})

@app.route('/<filename>')
def frontend_files(filename):
    if filename.endswith(('.js', '.css', '.html', '.ico', '.png', '.jpg', '.svg')):
        frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
        return send_from_directory(frontend_dir, filename)
    return jsonify({"error": "Not found"}), 404

@app.route('/')
def index():
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
    return send_from_directory(frontend_dir, 'index.html')

if __name__ == '__main__':
    try:
        initialize_knowledge_base()
    except Exception as e:
        print(f"Knowledge base load failed: {e}")
    app.run(port=5001, debug=True)
