import os
import autogen
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

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


# --- 2. CONFIGURE NVIDIA NIM ---
api_key = os.getenv("NVIDIA_API_KEY")
if not api_key:
    raise ValueError("NVIDIA_API_KEY not found in .env file or environment variables.")

# --- UNIFIED & CORRECTED MODEL CONFIGURATION ---
# We will use the same powerful, tool-capable model for all agents to ensure compatibility.
llm_config = {
    "model": "meta/llama-3.1-70b-instruct",
    "api_key": api_key,
    "base_url": "https://integrate.api.nvidia.com/v1"
}


# --- 3. SETUP AUTOGEN WORKFLOW ---
planner = create_planner_agent(llm_config)
coder = create_coder_agent(llm_config)

# The validator is an AssistantAgent that DECIDES to use the tool.
# We update its llm_config to make it aware of the tool's schema.
llm_config_validator = llm_config.copy()
llm_config_validator["tools"] = [
    {
        "type": "function",
        "function": {
            "name": "run_iec2c_compiler",
            "description": "Compiles Structured Text code to check for syntax errors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Structured Text code to compile.",
                    }
                },
                "required": ["code"],
            },
        },
    }
]
validator = create_validator_agent(llm_config_validator)

# The user_proxy is a UserProxyAgent that EXECUTES the tool call.
user_proxy = autogen.UserProxyAgent(
    name="UserProxy",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=10,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"use_docker": False},
    # Register the function for execution
    function_map={"run_iec2c_compiler": run_iec2c_compiler}
)

groupchat = autogen.GroupChat(
    agents=[user_proxy, planner, coder, validator],
    messages=[],
    max_round=12,
)

manager = autogen.GroupChatManager(
    groupchat=groupchat, 
    llm_config=llm_config
)

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
        if not prompt:
            return jsonify({"error": "Prompt is missing"}), 400

        # Reset agents to clear previous conversations
        user_proxy.reset()
        manager.reset()

        initial_message = f"""The user wants to generate Structured Text code for the following task: '{prompt}'.
        First, the Planner will create a plan.
        Next, the Coder will write the code based on the plan.
        Finally, the Validator will use the 'run_iec2c_compiler' tool to check the code."""

        # The UserProxy now initiates the chat
        user_proxy.initiate_chat(manager, message=initial_message)

        chat_history = user_proxy.chat_messages[manager]
        
        # --- NEW LOGIC: Find the BEST successfully compiled code ---
        best_code = "No code was generated."
        final_validation_message = "No validation was performed."
        success = False

        # Find the first piece of code that was successfully compiled
        for i, msg in enumerate(chat_history):
            # Check if the current message is from the Coder
            if msg.get('name') == 'Coder' and msg.get('content'):
                # Look ahead in the history for the corresponding tool result
                for next_msg in chat_history[i+1:]:
                    if next_msg.get('role') == 'tool':
                        validation_result = next_msg.get('content', '')
                        if "Compilation Successful." in validation_result:
                            best_code = msg['content'].strip()
                            final_validation_message = validation_result
                            success = True
                            # Break out of both loops once we find the first success
                            break
                        # If we find a tool result (even a failure), stop looking for this Coder message
                        break 
            if success:
                break
        
        # If no code compiled successfully, fall back to the last attempt
        if not success:
            for msg in reversed(chat_history):
                if msg.get('name') == 'Coder' and msg.get('content'):
                    best_code = msg['content'].strip()
                    break
            for msg in reversed(chat_history):
                if msg.get('role') == 'tool':
                    final_validation_message = msg['content'].strip()
                    break

        # --- End of new logic ---

        formatted_history = []
        for msg in chat_history:
            role = msg.get('name', msg.get('role'))
            content = msg.get('content')
            
            if role == 'tool':
                role = "UserProxy (Tool Result)"
            
            if not role or not content:
                continue

            if "tool_calls" in msg:
                continue

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

# --- 5. RUN THE APPLICATION ---
if __name__ == '__main__':
    app.run(debug=True, port=5001)
