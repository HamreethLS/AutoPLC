import autogen
from backend.tools.knowledge_base import query_knowledge_base

def create_knowledge_agent(llm_config):
    """Creates and returns the Knowledge Agent."""
    # Create a separate llm_config for the agent that includes the tool
    agent_llm_config = llm_config.copy()
    agent_llm_config["tools"] = [
        {
            "type": "function",
            "function": {
                "name": "query_knowledge_base",
                "description": "Queries the IEC 61131-3 knowledge base for specific programming rules, syntax, or concepts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query_text": {
                            "type": "string",
                            "description": "The specific question or topic to search for in the knowledge base.",
                        }
                    },
                    "required": ["query_text"],
                },
            },
        }
    ]

    return autogen.AssistantAgent(
        name="KnowledgeAgent",
        llm_config=agent_llm_config,
        system_message="""You are a knowledge base expert for the IEC 61131-3 standard.
        Your role is to answer questions from other agents by using the `query_knowledge_base` tool.
        Provide the retrieved information clearly and concisely. Do not add any extra information or apologies if the tool returns no results.
        Just state the facts from the knowledge base."""
    )
