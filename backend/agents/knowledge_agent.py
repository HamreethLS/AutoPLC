import autogen
from backend.tools.knowledge_base import query_knowledge_base

def create_knowledge_agent(llm_config):
    """Creates and returns the Knowledge Agent."""
    agent_llm_config = llm_config.copy()
    agent_llm_config["tools"] = [{
        "type": "function",
        "function": {
            "name": "query_knowledge_base",
            "description": "Queries the PLC programming knowledge base for IEC rules, syntax, and best practices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The specific PLC programming rules or syntax question."}
                },
                "required": ["query"]
            }
        }
    }]
    class SafeAssistantAgent(autogen.AssistantAgent):
        def on_tool_result(self, tool_result, *args, **kwargs):
            return tool_result if tool_result and str(tool_result).strip() else "No information could be retrieved for this query."
    return SafeAssistantAgent(
        name="KnowledgeAgent",
        llm_config=agent_llm_config,
        system_message="""You are a Knowledge Base Bot. Your only purpose is to answer IEC 61131-3 programming questions by calling the `query_knowledge_base` tool.
CRITICAL:
1. Your ONLY action is to call the tool with the agent's query.
2. Never answer from memory. Do not plan. Do not write code.
3. Always return exactly what the tool returns to the asking agent.
 - Never say you will continue later, and never leave a response unfinished.
"""
    )
