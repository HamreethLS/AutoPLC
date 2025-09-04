import autogen
from backend.tools.retrieval_tools import search_tavily, scrape_with_playwright

def create_retrieval_agent(llm_config):
    """Creates and returns the Retrieval Agent."""
    agent_llm_config = llm_config.copy()
    agent_llm_config["tools"] = [
        {
            "type": "function",
            "function": {
                "name": "search_tavily",
                "description": "Web search for technical documentation or PLC specs.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string", "description": "Search query."}},
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "scrape_with_playwright",
                "description": "Scrape a specific URL’s main visible text. Use after finding a promising result.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string", "description": "URL to scrape."}},
                    "required": ["url"]
                }
            }
        }
    ]
    class SafeAssistantAgent(autogen.AssistantAgent):
        def on_tool_result(self, tool_result, *args, **kwargs):
            return tool_result if tool_result and str(tool_result).strip() else "No information could be retrieved for this query."
    return SafeAssistantAgent(
        name="RetrievalAgent",
        llm_config=agent_llm_config,
        system_message="""You are a Retrieval Specialist. Use the `search_tavily` tool first to find technical sites/documentation. If a promising URL is found, use `scrape_with_playwright` to extract details from that specific page. Only return information from tools.
"""
    )
