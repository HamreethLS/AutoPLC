"""
Enhanced Coder Agent with robust code generation and error recovery
"""

import re
import asyncio
from typing import Dict, List, Optional, Any

from backend.utils.nim_client import enhanced_nim_client

class CoderAgent:
    """Enhanced coder with multiple generation strategies and error recovery"""
    
    def __init__(self):
        self.code_patterns = {
            "motor_control": self._get_motor_template(),
            "conveyor": self._get_conveyor_template(),
            "sequential": self._get_sequential_template(),
            "safety": self._get_safety_template(),
            "generic": self._get_generic_template()
        }
    
    async def generate_code(
        self, 
        plan: str, 
        knowledge: Optional[str] = None,
        research_data: Optional[str] = None
    ) -> str:
        """Generate robust IEC 61131-3 Structured Text code"""
        
        # Determine code pattern based on plan
        pattern_type = self._identify_pattern(plan)
        template = self.code_patterns[pattern_type]
        
        # Build comprehensive prompt
        coding_prompt = self._build_coding_prompt(plan, knowledge, research_data, template)
        
        # Multiple generation attempts with different strategies
        for attempt in range(3):
            try:
                code = await self._generate_with_strategy(coding_prompt, attempt)
                
                # Validate generated code
                if self._validate_code_structure(code): # _validate_code_structure works on the raw response
                    return self._extract_and_clean_code(code) # Return ONLY the extracted code
                
            except Exception as e:
                if attempt == 2:  # Last attempt
                    return self._create_fallback_code(plan)
                continue
        
        return self._create_fallback_code(plan)
    
    async def refine_code(
        self, 
        original_code: str, 
        feedback: str, 
        validation_report: str
    ) -> str:
        """Refine code based on feedback and validation results"""
        
        refinement_prompt = f"""
You are an expert IEC 61131-3 programmer. Refine the following code based on feedback.

ORIGINAL CODE:
{original_code}

VALIDATION REPORT:
{validation_report}

USER FEEDBACK:
{feedback}

REQUIREMENTS:
1. Fix any compilation errors mentioned in the validation report
2. Address all points in the user feedback
3. **Critically, re-evaluate the entire logic.** Do not repeat logical fallacies from the original code (e.g., `var := (X OR NOT X)` is always true and is not valid validation).
4. Maintain IEC 61131-3 compliance
5. Keep the same overall functionality, but improve the structure for clarity and correctness.
5. Use proper comment syntax: (* comment *)
6. Ensure all variables are declared in VAR...END_VAR

Provide ONLY the complete, corrected Structured Text code in a single code block.
"""
        
        try:
            refined_code = await enhanced_nim_client.call_agent_simple(
                agent_role="coder",
                prompt=refinement_prompt,
                temperature=0.1,
                max_tokens=1500
            )
            
            return self._extract_and_clean_code(refined_code)
            
        except Exception as e:
            return original_code  # Return original if refinement fails
    
    def _identify_pattern(self, plan: str) -> str:
        """Identify the appropriate code pattern based on the plan"""
        plan_lower = plan.lower()
        
        if any(word in plan_lower for word in ['motor', 'pump', 'valve', 'actuator']):
            return "motor_control"
        elif any(word in plan_lower for word in ['conveyor', 'belt', 'transport']):
            return "conveyor"
        elif any(word in plan_lower for word in ['sequence', 'step', 'stage', 'phase']):
            return "sequential"
        elif any(word in plan_lower for word in ['safety', 'emergency', 'interlock']):
            return "safety"
        else:
            return "generic"
    
    async def _generate_with_strategy(self, prompt: str, attempt: int) -> str:
        """Generate code with different strategies for robustness"""
        
        strategies = [
            {"temperature": 0.1, "max_tokens": 1024},  # Conservative
            {"temperature": 0.2, "max_tokens": 1200},  # Moderate
            {"temperature": 0.15, "max_tokens": 800}   # Focused
        ]
        
        strategy = strategies[attempt % len(strategies)]
        
        return await enhanced_nim_client.call_agent_simple(
            agent_role="coder",
            prompt=prompt,
            **strategy
        )
    
    def _build_coding_prompt(
        self, 
        plan: str, 
        knowledge: Optional[str], 
        research_data: Optional[str],
        template: str
    ) -> str:
        """Build a comprehensive coding prompt"""
        
        knowledge_section = f"\nKNOWLEDGE CONTEXT:\n{knowledge}" if knowledge else ""
        research_section = f"\nRESEARCH DATA:\n{research_data}" if research_data else ""
        
        return f"""
{template}

IMPLEMENTATION PLAN:
{plan}
{knowledge_section}
{research_section}

CRITICAL REQUIREMENTS:
1. Output ONLY the complete Structured Text code
2. Use proper IEC 61131-3 syntax. Pay very close attention to any MATIEC-specific syntax rules mentioned in the knowledge context.
3. All variables must be declared in VAR...END_VAR block
4. Structure the program correctly. If the knowledge context provides specific structural rules (e.g., regarding the use of the `BEGIN` keyword), you MUST follow them. Otherwise, place executable logic between `BEGIN` and `END_PROGRAM`.
5. Use comment syntax: (* comment *)
6. No forbidden function blocks (TON, TOF, etc.) - use manual implementations
7. Ensure proper variable addressing with AT %I and %Q
8. Include descriptive comments explaining the logic

Generate the complete program now:
"""
    
    def _validate_code_structure(self, code: str) -> bool:
        """Validate that the code has proper IEC structure"""
        
        # Extract actual code
        actual_code = self._extract_and_clean_code(code)
        
        if not actual_code:
            return False
        
        # Check for essential IEC elements
        required_elements = [
            r'PROGRAM\s+\w+',
            r'VAR.*?END_VAR',
            r'BEGIN',
            r'END_PROGRAM'
        ]
        
        return all(re.search(pattern, actual_code, re.DOTALL | re.IGNORECASE) 
                  for pattern in required_elements)
    
    def _extract_and_clean_code(self, response: str) -> str:
        """Extract and clean the ST code from the response"""
        
        # Try to find code within markdown blocks first
        code_block_match = re.search(r'```(?:st|iec|structuredtext)?\s*\n(.*?)\n```', response, re.DOTALL | re.IGNORECASE)
        if code_block_match:
            code = code_block_match.group(1).strip()
            if len(code) > 50:  # Reasonable minimum length
                return self._clean_and_format_code(code)

        # If no markdown block, try to extract PROGRAM block directly
        program_match = re.search(r'(PROGRAM\s+\w+.*?END_PROGRAM)', response, re.DOTALL | re.IGNORECASE)
        if program_match:
            return self._clean_and_format_code(program_match.group(1))
        
        # If all else fails, return the raw response if it looks like code
        if "PROGRAM" in response.upper() and "END_PROGRAM" in response.upper():
            return self._clean_and_format_code(response)

        return "" # Return empty if no code is found
    
    def _clean_and_format_code(self, code: str) -> str:
        """Clean and format the code"""
        
        # Remove extra whitespace and normalize line endings
        lines = [line.strip() for line in code.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines

        # Proactive correction of common syntax errors
        lines = [re.sub(r'^\s*ELSE\s+IF', 'ELSIF', line, flags=re.IGNORECASE) for line in lines]
        
        # Basic formatting
        formatted_lines = []
        indent_level = 0
        
        for line in lines:
            line_upper = line.upper()
            
            # Decrease indent for END statements
            if any(line_upper.startswith(end) for end in ['END_VAR', 'END_IF', 'END_CASE', 'END_PROGRAM']):
                indent_level = max(0, indent_level - 1)
            
            # Add indented line
            formatted_lines.append('    ' * indent_level + line)
            
            # Increase indent after BEGIN, IF, CASE, VAR
            if any(line_upper.startswith(begin) for begin in ['VAR', 'BEGIN', 'IF ', 'CASE ']):
                indent_level += 1
        
        return '\n'.join(formatted_lines)
    
    def _create_fallback_code(self, plan: str) -> str:
        """Create basic fallback code when generation fails"""
        
        return """PROGRAM FallbackProgram
VAR
    (* Input variables *)
    InputSignal AT %I0.0 : BOOL;
    
    (* Output variables *)
    OutputSignal AT %Q0.0 : BOOL;
END_VAR

BEGIN
    (* Basic logic implementation *)
    IF InputSignal THEN
        OutputSignal := TRUE;
    ELSE
        OutputSignal := FALSE;
    END_IF;
END_PROGRAM"""
    
    def _get_motor_template(self) -> str:
        return """You are an expert in motor control programming. Generate IEC 61131-3 Structured Text for motor/actuator control with proper start/stop logic, safety interlocks, and status monitoring."""
    
    def _get_conveyor_template(self) -> str:
        return """You are an expert in conveyor system programming. Generate IEC 61131-3 Structured Text for conveyor control with proper direction control, speed management, and safety features."""
    
    def _get_sequential_template(self) -> str:
        return """You are an expert in sequential control programming. Generate IEC 61131-3 Structured Text for step-by-step processes with proper state management and transitions."""
    
    def _get_safety_template(self) -> str:
        return """You are an expert in safety-critical PLC programming. Generate IEC 61131-3 Structured Text with comprehensive safety logic, emergency stops, and fail-safe operation."""
    
    def _get_generic_template(self) -> str:
        return """You are an expert IEC 61131-3 Structured Text programmer. Generate clean, compliant, and well-documented code following all IEC standards and best practices."""
