import autogen

def create_validator_agent(llm_config):
    """Creates and returns the Validator as an AssistantAgent."""
    return autogen.AssistantAgent(
        name="Validator",
        llm_config=llm_config,
        system_message="""You are a code validator. Your role is to take the ST code provided by the Coder
        and call the 'run_iec2c_compiler' tool to check it.
        Based on the tool's output, either approve the code by replying with 'TERMINATE' or provide clear, concise feedback to the Coder on what to fix."""
    )
