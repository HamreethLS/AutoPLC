"""
Enhanced Planner Agent with context-aware planning and recovery strategies
"""

import asyncio
from typing import Dict, List, Optional, Any

from backend.utils.nim_client import enhanced_nim_client
from backend.tools.knowledge_base import query_knowledge_base

class PlannerAgent:
    """Enhanced planner with dynamic planning strategies"""
    
    def __init__(self):
        self.planning_templates = {
            "simple": self._get_simple_template(),
            "complex": self._get_complex_template(),
            "safety_critical": self._get_safety_template()
        }
    
    async def create_plan(self, prompt: str, knowledge_context: Optional[str] = None) -> str:
        """Create a detailed implementation plan with context awareness"""
        
        # Assess complexity to choose appropriate template
        complexity = self._assess_complexity(prompt)
        template = self.planning_templates[complexity]
        
        # Enhance prompt with knowledge context
        enhanced_prompt = self._build_planning_prompt(prompt, knowledge_context, template)
        
        try:
            plan = await enhanced_nim_client.call_agent_simple(
                agent_role="planner",
                prompt=enhanced_prompt,
                temperature=0.1,
                max_tokens=1024
            )
            
            # Post-process and validate plan
            return self._validate_and_enhance_plan(plan, prompt)
            
        except Exception as e:
            # Fallback planning strategy
            return self._create_fallback_plan(prompt)
    
    def _assess_complexity(self, prompt: str) -> str:
        """Assess the complexity of the request"""
        prompt_lower = prompt.lower()
        
        # Safety-critical indicators
        safety_keywords = ['safety', 'emergency', 'interlock', 'fail-safe', 'alarm']
        if any(keyword in prompt_lower for keyword in safety_keywords):
            return "safety_critical"
        
        # Complex indicators
        complex_keywords = [
            'communication', 'protocol', 'network', 'multi-step', 'sequence',
            'timer', 'counter', 'pid', 'analog', 'recipe'
        ]
        if any(keyword in prompt_lower for keyword in complex_keywords):
            return "complex"
        
        return "simple"
    
    def _build_planning_prompt(self, prompt: str, knowledge: Optional[str], template: str) -> str:
        """Build an enhanced planning prompt"""
        
        knowledge_section = ""
        if knowledge:
            knowledge_section = f"""
            
RELEVANT IEC KNOWLEDGE:
{knowledge}

Use this knowledge to ensure compliance and best practices.
"""
        
        return f"""
{template}

USER REQUEST:
{prompt}
{knowledge_section}

Create a detailed implementation plan that covers:
1. Variable declarations with proper IEC addressing
2. Logic implementation strategy
3. Safety considerations
4. Compliance requirements
5. Testing approach

Provide the plan as numbered steps with clear technical details.
"""
    
    def _get_simple_template(self) -> str:
        return """
You are an expert PLC programmer creating implementation plans for basic control logic.
Focus on clear, simple implementations following IEC 61131-3 standards.
"""
    
    def _get_complex_template(self) -> str:
        return """
You are an expert PLC programmer creating implementation plans for complex industrial systems.
Consider multi-step processes, timing requirements, error handling, and system integration.
Ensure robust implementation with proper state management and error recovery.
"""
    
    def _get_safety_template(self) -> str:
        return """
You are an expert in safety-critical PLC programming following IEC 61131-3 and IEC 61508 standards.
Priority order: SAFETY FIRST, then functionality, then efficiency.
Include fail-safe logic, emergency stops, and comprehensive interlocking.
"""
    
    def _validate_and_enhance_plan(self, plan: str, original_prompt: str) -> str:
        """Validate and enhance the generated plan"""
        
        # If the plan is empty or just whitespace, the LLM failed. Use the fallback.
        if not plan or len(plan.strip()) < 20:
            return self._create_fallback_plan(original_prompt)

        # Check for essential elements
        essential_elements = [
            'variable', 'declaration', 'logic', 'IEC', 'step'
        ]
        
        missing_elements = [
            element for element in essential_elements 
            if element.lower() not in plan.lower()
        ]
        
        if missing_elements:
            # Enhance plan with missing elements
            enhancement = f"""
            
PLAN ENHANCEMENT:
- Ensure proper variable declarations for all I/O points
- Include IEC 61131-3 compliance checks
- Add structured logic implementation steps
"""
            plan += enhancement
        
        return plan
    
    def _create_fallback_plan(self, prompt: str) -> str:
        """Create a basic fallback plan when normal planning fails"""
        
        return f"""
FALLBACK IMPLEMENTATION PLAN:

1. ANALYZE REQUIREMENTS
   - Parse user request: {prompt}
   - Identify required inputs and outputs
   - Determine control logic type

2. VARIABLE DECLARATIONS
   - Declare all inputs with AT %I addresses
   - Declare all outputs with AT %Q addresses  
   - Use descriptive variable names
   - Include proper IEC data types

3. IMPLEMENT LOGIC
   - Use simple IF-THEN-ELSE structures
   - Avoid complex nesting
   - Include proper comments using (* ... *)
   - Ensure scan-cycle compatibility

4. SAFETY CONSIDERATIONS
   - Add emergency stop logic if applicable
   - Include input validation
   - Implement fail-safe defaults

5. VALIDATION
   - Check IEC 61131-3 syntax compliance
   - Verify all variables are declared
   - Test logic flow
"""

    # Additional agent methods for refinement and feedback
    async def revise_plan(self, original_plan: str, feedback: str, context: Dict[str, Any]) -> str:
        """Revise an existing plan based on feedback"""
        
        revision_prompt = f"""
ORIGINAL PLAN:
{original_plan}

FEEDBACK TO ADDRESS:
{feedback}

CONTEXT:
{context}

Please revise the implementation plan to address the feedback while maintaining:
1. IEC 61131-3 compliance
2. Clear technical specifications
3. Safety considerations
4. Implementability

Provide the COMPLETE revised plan.
"""
        
        try:
            return await enhanced_nim_client.call_agent_simple(
                agent_role="planner",
                prompt=revision_prompt,
                temperature=0.2,
                max_tokens=1200
            )
        except Exception as e:
            return f"{original_plan}\n\nREVISION FAILED: {str(e)}"
