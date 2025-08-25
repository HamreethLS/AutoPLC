import autogen

def create_coder_agent(llm_config):
    """Creates and returns the Coder agent."""
    return autogen.AssistantAgent(
        name="Coder",
        llm_config=llm_config,
        system_message="""You are a specialist in IEC 61131-3 Structured Text (ST) programming.
        Your task is to write ST code based on the plan provided by the Planner.
        IMPORTANT: You must only output the raw ST code inside a single code block. Do not include any explanations,
        markdown formatting (like ```st ... ```), or conversational text.
        If you receive feedback from the Validator, you must attempt to fix the code and output the full, corrected program. If the feedback is unclear, try your best to interpret it or ask for clarification, but always provide a complete code block in your response."""
    )
