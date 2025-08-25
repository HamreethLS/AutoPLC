import autogen

def create_planner_agent(llm_config):
    """Creates and returns the Planner agent."""
    return autogen.AssistantAgent(
        name="Planner",
        llm_config=llm_config,
        system_message="""You are an expert PLC programmer. Your role is to analyze a user's request
        and create a clear, step-by-step plan for generating Structured Text code.
        The plan should be simple and direct for the Coder to follow.
        Do not write any code yourself. Just provide the plan."""
    )
