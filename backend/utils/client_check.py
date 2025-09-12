from nim_client import RequestPriority , enhanced_nim_client
import asyncio
# Simple agent call
response =enhanced_nim_client.call_agent_simple(
    agent_role="planner",
    prompt="Create a plan for motor control system",
    priority=RequestPriority.HIGH
)

# Tool calling
tools = [{"type": "function", "function": {"name": "validate_code"}}]
response = enhanced_nim_client.call_with_tools(
    agent_role="validator", 
    messages=[{"role": "user", "content": "Check this code"}],
    tools=tools
)

# Performance monitoring
stats = enhanced_nim_client.get_performance_stats()
print(f"Success rate: {stats['overall']['success_rate']:.2f}")
