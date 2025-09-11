"""Code generator agent for PLC Structured Text programming."""

import logging
from typing import Dict, Any, List
from datetime import datetime
import re

from agents.base_agent import LLMAgent
from models.schemas import AgentRole, AgentTask, GeneratedCode, PLCLanguage


class GeneratorAgent(LLMAgent):
    """Agent responsible for generating PLC code from requirements and plans."""
    
    def __init__(self, llm=None):
        super().__init__(
            role=AgentRole.GENERATOR,
            name="PLC Code Generator",
            description="Generates IEC 61131-3 compliant PLC code from structured plans",
            llm=llm
        )
        
        # Code generation templates
        self.code_templates = {
            "program_header": """
PROGRAM {program_name}
VAR
{variables}
END_VAR

{code_body}
END_PROGRAM
""",
            "function_block": """
FUNCTION_BLOCK {fb_name}
VAR_INPUT
{input_vars}
END_VAR
VAR_OUTPUT
{output_vars}
END_VAR
VAR
{internal_vars}
END_VAR

{fb_body}
END_FUNCTION_BLOCK
""",
            "function": """
FUNCTION {func_name} : {return_type}
VAR_INPUT
{input_vars}
END_VAR
VAR
{local_vars}
END_VAR

{func_body}
END_FUNCTION
"""
        }
        
        # Common PLC patterns
        self.patterns = {
            "motor_control": {
                "variables": [
                    "start_cmd : BOOL := FALSE;",
                    "stop_cmd : BOOL := FALSE;",
                    "motor_run : BOOL := FALSE;",
                    "motor_feedback : BOOL := FALSE;",
                    "fault_reset : BOOL := FALSE;",
                    "motor_fault : BOOL := FALSE;"
                ],
                "logic": """
// Motor start/stop logic with fault handling
motor_run := (start_cmd OR motor_run) AND NOT stop_cmd AND NOT motor_fault AND motor_feedback;

// Fault detection
IF motor_run AND NOT motor_feedback THEN
    motor_fault := TRUE;
END_IF;

// Fault reset
IF fault_reset THEN
    motor_fault := FALSE;
END_IF;
"""
            },
            "analog_scaling": {
                "variables": [
                    "raw_input : INT;",
                    "scaled_output : REAL;",
                    "min_raw : INT := 0;",
                    "max_raw : INT := 4095;",
                    "min_eng : REAL := 0.0;",
                    "max_eng : REAL := 100.0;"
                ],
                "logic": """
// Linear scaling of analog input
IF max_raw > min_raw THEN
    scaled_output := min_eng + (raw_input - min_raw) * (max_eng - min_eng) / (max_raw - min_raw);
ELSE
    scaled_output := min_eng;
END_IF;

// Limit output to engineering range
scaled_output := LIMIT(min_eng, scaled_output, max_eng);
"""
            },
            "timer_sequence": {
                "variables": [
                    "step : INT := 0;",
                    "timer1 : TON;",
                    "start_sequence : BOOL := FALSE;",
                    "sequence_complete : BOOL := FALSE;",
                    "sequence_fault : BOOL := FALSE;"
                ],
                "logic": """
// Timer-based sequence control
CASE step OF
    0: // Wait for start
        IF start_sequence THEN
            step := 1;
        END_IF;
        
    1: // First step with timer
        timer1(IN := TRUE, PT := T#5s);
        IF timer1.Q THEN
            step := 2;
            timer1(IN := FALSE);
        END_IF;
        
    2: // Sequence complete
        sequence_complete := TRUE;
        IF NOT start_sequence THEN
            step := 0;
            sequence_complete := FALSE;
        END_IF;
END_CASE;
"""
            }
        }
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the generator agent."""
        return """
You are a PLC Code Generator Agent specialized in creating IEC 61131-3 compliant Structured Text (ST) code.

Your responsibilities:
1. Generate syntactically correct ST code from structured plans
2. Follow IEC 61131-3 programming standards and conventions
3. Implement safety-critical logic with appropriate fail-safe behavior
4. Create modular, maintainable, and well-documented code
5. Include proper variable declarations and type safety
6. Implement error handling and diagnostic features

Code generation principles:
- Use clear, descriptive variable names
- Follow consistent coding style and formatting
- Include comprehensive comments for complex logic
- Implement proper data types and ranges
- Use proven programming patterns and structures
- Consider real-time execution constraints
- Include safety interlocks and fault handling
- Plan for future maintenance and modifications

Safety considerations:
- Implement fail-safe logic (fail to safe state)
- Use appropriate data types and ranges
- Include input validation and bounds checking
- Implement watchdog timers for critical functions
- Use proven safety patterns and architectures
- Document all safety-critical code sections

Always generate production-ready code that meets industrial automation standards.
"""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a code generation task."""
        task_type = task.task_type
        input_data = task.input_data
        
        if task_type == "generate_code":
            return await self._generate_code(input_data)
        elif task_type == "generate_function":
            return await self._generate_function(input_data)
        elif task_type == "generate_function_block":
            return await self._generate_function_block(input_data)
        elif task_type == "refactor_code":
            return await self._refactor_code(input_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _generate_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate complete PLC program code."""
        requirement = input_data.get("requirement", {})
        task_plan = input_data.get("previous_results", {}).get("create_plan", {}).get("task_plan", {})
        knowledge_context = input_data.get("previous_results", {}).get("retrieve_knowledge", {})
        
        # Extract requirements
        description = requirement.get("description", "")
        language = requirement.get("language", "st")
        safety_level = requirement.get("safety_level", 1)
        constraints = requirement.get("constraints", {})
        
        # Determine program structure
        program_name = self._generate_program_name(description)
        
        # Generate variables based on task type and requirements
        variables = self._generate_variables(description, task_plan, safety_level)
        
        # Generate main program logic
        code_body = await self._generate_program_logic(description, task_plan, knowledge_context, safety_level)
        
        # Assemble complete program
        complete_code = self.code_templates["program_header"].format(
            program_name=program_name,
            variables="\n".join(f"    {var}" for var in variables),
            code_body=code_body
        )
        
        # Extract metadata
        functions_used = self._extract_functions(complete_code)
        variables_declared = self._extract_variables(complete_code)
        
        # Create generated code object
        generated_code = GeneratedCode(
            requirement_id=requirement.get("id"),
            plan_id=task_plan.get("id"),
            language=PLCLanguage.STRUCTURED_TEXT,
            code=complete_code,
            variables=variables_declared,
            functions=functions_used,
            metadata={
                "program_name": program_name,
                "safety_level": safety_level,
                "generation_method": "template_based",
                "knowledge_sources": list(knowledge_context.keys()) if knowledge_context else [],
                "complexity_score": len(complete_code.split('\n')),
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
        return {
            "generated_code": generated_code.dict(),
            "program_name": program_name,
            "line_count": len(complete_code.split('\n')),
            "variable_count": len(variables_declared),
            "function_count": len(functions_used),
            "safety_features": self._identify_safety_features(complete_code),
            "generation_stats": {
                "template_used": True,
                "patterns_applied": self._identify_patterns_used(description),
                "generation_time": datetime.utcnow().isoformat()
            }
        }
    
    async def _generate_function(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a specific function."""
        function_spec = input_data.get("function_spec", {})
        
        func_name = function_spec.get("name", "CustomFunction")
        return_type = function_spec.get("return_type", "BOOL")
        inputs = function_spec.get("inputs", [])
        logic = function_spec.get("logic", "// Function logic here")
        
        # Generate input variable declarations
        input_vars = []
        for inp in inputs:
            input_vars.append(f"    {inp['name']} : {inp['type']};")
        
        # Generate function code
        function_code = self.code_templates["function"].format(
            func_name=func_name,
            return_type=return_type,
            input_vars="\n".join(input_vars),
            local_vars="    // Local variables",
            func_body=f"    {logic}\n    {func_name} := TRUE; // Default return"
        )
        
        return {
            "function_code": function_code,
            "function_name": func_name,
            "return_type": return_type,
            "input_count": len(inputs)
        }
    
    async def _generate_function_block(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a function block."""
        fb_spec = input_data.get("fb_spec", {})
        
        fb_name = fb_spec.get("name", "CustomFB")
        inputs = fb_spec.get("inputs", [])
        outputs = fb_spec.get("outputs", [])
        logic = fb_spec.get("logic", "// Function block logic here")
        
        # Generate variable declarations
        input_vars = [f"    {inp['name']} : {inp['type']};" for inp in inputs]
        output_vars = [f"    {out['name']} : {out['type']};" for out in outputs]
        
        # Generate function block code
        fb_code = self.code_templates["function_block"].format(
            fb_name=fb_name,
            input_vars="\n".join(input_vars),
            output_vars="\n".join(output_vars),
            internal_vars="    // Internal variables",
            fb_body=f"    {logic}"
        )
        
        return {
            "function_block_code": fb_code,
            "fb_name": fb_name,
            "input_count": len(inputs),
            "output_count": len(outputs)
        }
    
    async def _refactor_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Refactor existing code for improvements."""
        existing_code = input_data.get("existing_code", "")
        refactor_goals = input_data.get("goals", ["readability", "performance"])
        
        # Apply refactoring based on goals
        refactored_code = existing_code
        changes_made = []
        
        if "readability" in refactor_goals:
            # Add comments and improve formatting
            refactored_code = self._improve_readability(refactored_code)
            changes_made.append("Improved code readability and comments")
        
        if "performance" in refactor_goals:
            # Optimize for performance
            refactored_code = self._optimize_performance(refactored_code)
            changes_made.append("Applied performance optimizations")
        
        if "safety" in refactor_goals:
            # Add safety features
            refactored_code = self._enhance_safety(refactored_code)
            changes_made.append("Enhanced safety features")
        
        return {
            "refactored_code": refactored_code,
            "changes_made": changes_made,
            "improvement_score": len(changes_made) * 25  # Simple scoring
        }
    
    def _generate_program_name(self, description: str) -> str:
        """Generate a program name from description."""
        # Extract key words and create a program name
        words = re.findall(r'\b[A-Za-z]+\b', description)
        key_words = [word.capitalize() for word in words[:3] if len(word) > 3]
        
        if not key_words:
            return "MainProgram"
        
        return "".join(key_words) + "Control"
    
    def _generate_variables(self, description: str, task_plan: Dict, safety_level: int) -> List[str]:
        """Generate variable declarations based on requirements."""
        variables = []
        
        # Determine pattern type
        pattern_type = self._identify_patterns_used(description)[0] if self._identify_patterns_used(description) else "motor_control"
        
        # Get base variables from pattern
        if pattern_type in self.patterns:
            variables.extend(self.patterns[pattern_type]["variables"])
        
        # Add safety variables if required
        if safety_level > 1:
            variables.extend([
                "safety_ok : BOOL := TRUE;",
                "emergency_stop : BOOL := FALSE;",
                "safety_fault : BOOL := FALSE;"
            ])
        
        # Add common system variables
        variables.extend([
            "system_enable : BOOL := FALSE;",
            "system_fault : BOOL := FALSE;",
            "heartbeat : BOOL := FALSE;"
        ])
        
        return variables
    
    async def _generate_program_logic(self, description: str, task_plan: Dict, knowledge_context: Dict, safety_level: int) -> str:
        """Generate the main program logic."""
        logic_parts = []
        
        # Add header comment
        logic_parts.append(f"// Generated PLC program for: {description}")
        logic_parts.append(f"// Safety Level: SIL {safety_level}")
        logic_parts.append(f"// Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
        logic_parts.append("")
        
        # Add safety logic if required
        if safety_level > 1:
            logic_parts.append("// Safety system checks")
            logic_parts.append("safety_ok := NOT emergency_stop AND NOT safety_fault;")
            logic_parts.append("system_enable := system_enable AND safety_ok;")
            logic_parts.append("")
        
        # Determine and add main logic pattern
        patterns_used = self._identify_patterns_used(description)
        for pattern in patterns_used:
            if pattern in self.patterns:
                logic_parts.append(f"// {pattern.replace('_', ' ').title()} Logic")
                logic_parts.append(self.patterns[pattern]["logic"])
                logic_parts.append("")
        
        # Add system heartbeat
        logic_parts.append("// System heartbeat")
        logic_parts.append("heartbeat := NOT heartbeat;")
        
        return "\n".join(logic_parts)
    
    def _identify_patterns_used(self, description: str) -> List[str]:
        """Identify which patterns to use based on description."""
        description_lower = description.lower()
        patterns = []
        
        if any(word in description_lower for word in ["motor", "pump", "fan"]):
            patterns.append("motor_control")
        
        if any(word in description_lower for word in ["analog", "temperature", "pressure"]):
            patterns.append("analog_scaling")
        
        if any(word in description_lower for word in ["sequence", "timer", "step"]):
            patterns.append("timer_sequence")
        
        return patterns if patterns else ["motor_control"]
    
    def _extract_functions(self, code: str) -> List[Dict[str, Any]]:
        """Extract function information from code."""
        functions = []
        
        # Find function calls
        function_calls = re.findall(r'(\w+)\s*\(', code)
        for func_name in set(function_calls):
            if func_name.upper() not in ['IF', 'CASE', 'FOR', 'WHILE']:
                functions.append({
                    "name": func_name,
                    "type": "function_call",
                    "usage_count": function_calls.count(func_name)
                })
        
        return functions
    
    def _extract_variables(self, code: str) -> List[Dict[str, Any]]:
        """Extract variable information from code."""
        variables = []
        
        # Find variable declarations
        var_declarations = re.findall(r'(\w+)\s*:\s*(\w+)(?:\s*:=\s*([^;]+))?;', code)
        for var_name, var_type, default_value in var_declarations:
            variables.append({
                "name": var_name,
                "type": var_type,
                "default_value": default_value.strip() if default_value else None,
                "scope": "program"
            })
        
        return variables
    
    def _identify_safety_features(self, code: str) -> List[str]:
        """Identify safety features in the generated code."""
        features = []
        
        if "emergency_stop" in code:
            features.append("Emergency stop handling")
        
        if "safety_ok" in code:
            features.append("Safety system monitoring")
        
        if "fault" in code.lower():
            features.append("Fault detection and handling")
        
        if "LIMIT(" in code:
            features.append("Value limiting/clamping")
        
        if "watchdog" in code.lower():
            features.append("Watchdog timer")
        
        return features
    
    def _improve_readability(self, code: str) -> str:
        """Improve code readability."""
        lines = code.split('\n')
        improved_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('//'):
                # Add comment for complex lines
                if any(keyword in stripped for keyword in ['CASE', 'IF', 'FOR', 'WHILE']):
                    if not any(prev_line.strip().startswith('//') for prev_line in improved_lines[-2:]):
                        improved_lines.append(f"    // {stripped.split()[0]} logic")
            
            improved_lines.append(line)
        
        return '\n'.join(improved_lines)
    
    def _optimize_performance(self, code: str) -> str:
        """Apply performance optimizations."""
        # Simple optimizations - in practice this would be more sophisticated
        optimized = code
        
        # Replace multiple NOT operations
        optimized = re.sub(r'NOT\s+NOT\s+(\w+)', r'\1', optimized)
        
        # Optimize boolean expressions
        optimized = re.sub(r'(\w+)\s*=\s*TRUE', r'\1', optimized)
        optimized = re.sub(r'(\w+)\s*=\s*FALSE', r'NOT \1', optimized)
        
        return optimized
    
    def _enhance_safety(self, code: str) -> str:
        """Enhance safety features in code."""
        lines = code.split('\n')
        enhanced_lines = []
        
        for line in lines:
            enhanced_lines.append(line)
            
            # Add safety checks after critical operations
            if ':=' in line and any(keyword in line for keyword in ['motor', 'valve', 'pump']):
                var_name = line.split(':=')[0].strip()
                enhanced_lines.append(f"    // Safety check for {var_name}")
                enhanced_lines.append(f"    {var_name} := {var_name} AND safety_ok;")
        
        return '\n'.join(enhanced_lines)
