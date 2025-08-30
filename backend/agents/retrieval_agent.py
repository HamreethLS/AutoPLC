import autogen
from backend.tools.retrieval_tools import search_tavily, search_mouser

def create_retrieval_agent(llm_config):
    """Creates and returns the Retrieval Agent."""
    agent_llm_config = llm_config.copy()
    agent_llm_config["tools"] = [
        {
            "type": "function",
            "function": {
                "name": "search_tavily",
                "description": "Performs a web search for information on specific PLC models, hardware, or technical questions.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "The search query."}},
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_mouser",
                "description": "Looks up specifications for a specific electronic component part number.",
                "parameters": {
                    "type": "object",
                    "properties": {"part_number": {"type": "string", "description": "The component part number to search for."}},
                    "required": ["part_number"],
                },
            },
        },
    ]

    return autogen.AssistantAgent(
        name="RetrievalAgent",
        llm_config=agent_llm_config,
        system_message="""You are a Retrieval Specialist. Your job is to find external information when requested by other agents.
        Use the `search_tavily` tool for general questions about PLC models or standards.
        Use the `search_mouser` tool when you need data on a specific electronic component part number.
        Present the information you find clearly and concisely."""
    )
