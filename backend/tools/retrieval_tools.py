import os
import requests
from dotenv import load_dotenv

load_dotenv()

def search_tavily(query: str) -> str:
    """
    Performs a web search using the Tavily API to find information
    on specific PLC models, hardware, or technical standards.
    """
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "Error: TAVILY_API_KEY not found in .env file."

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "include_answer": True,
                "max_results": 3,
            },
        )
        response.raise_for_status()
        result = response.json()
        
        if "answer" in result and result["answer"]:
            return f"Tavily Search Answer: {result['answer']}"
            
        return f"Tavily Search Results:\n" + "\n".join(
            [f"- {res['title']}: {res['snippet']}" for res in result.get("results", [])]
        )
    except Exception as e:
        return f"Error performing Tavily search: {e}"


def search_mouser(part_number: str) -> str:
    """
    Searches the Mouser API for specifications of a specific electronic component.
    NOTE: This is a placeholder. A real implementation would require signing up for
    the Mouser API and handling a more complex request/response cycle.
    """
    api_key = os.getenv("MOUSER_API_KEY")
    if not api_key:
        return "Error: MOUSER_API_KEY not found in .env file. This is a placeholder function."

    # Placeholder logic
    print(f"--- (Placeholder) Pretending to search Mouser for: {part_number} ---")
    if "5570" in part_number:
        return f"Mouser Data for '{part_number}':\n- Category: Programmable Logic Controllers\n- Manufacturer: Rockwell Automation\n- Core Processor: ARM\n- Memory: 8 MB\n- Datasheet: Available on manufacturer website."
    else:
        return f"No specific data found for '{part_number}' in placeholder Mouser API."

