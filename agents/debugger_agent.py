"""Debugger agent for error handling and automated code fixes."""

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from agents.base_agent import LLMAgent
from models.schemas import AgentRole, AgentTask


class DebuggerAgent(LLMAgent):
    """Agent responsible for debugging code issues and providing automated fixes."""
    
    def __init__(self, llm=None):
        super().__init__(
            role=AgentRole.DEBUGGER,
            name="PLC Code Debugger",
            description="Debugs PLC code issues and provides automated fixes",
            llm=llm
        )
        
        # Common error patterns and their fixes
        self.error_patterns = {
            "missing_semicolon": {
                "pattern": r"(.+):=(.+)(?<!;)$",
                "fix": r"\1:=\2;",
                "description": "Add missing semicolon"
            },
            "unmatched_parentheses": {
                "pattern": r"([^()]*\([^()]*(?:\([^()]*\)[^()]*)*[^)]*)$",
                "fix": lambda match: match.group(0) + ")",
                "description": "Add missing closing parenthesis"
            },
            "double_negation": {
                "pattern": r"NOT\s+NOT\s+(\w+)",
                "fix": r"\1",
                "description": "Remove double negation"
            },
            "boolean_redundancy": {
                "pattern": r"(\w+)\s*=\s*TRUE",
                "fix": r"\1",
                "description": "Simplify boolean expression"
            },
            "case_sensitivity": {
                "pattern": r"\b(true|false)\b",
                "fix": lambda match: match.group(0).upper(),
                "description": "Fix case sensitivity for boolean values"
            }
        }
        
        # Safety fix patterns
        self.safety_fixes = {
            "add_emergency_stop": {
                "condition": lambda code: "emergency_stop" not in code.lower(),
                "fix": "emergency_stop : BOOL := FALSE;",
                "location": "variables",
                "description": "Add emergency stop variable"
            },
            "add_safety_interlock": {
                "condition": lambda code: "safety_ok" not in code.lower(),
                "fix": "safety_ok : BOOL := TRUE;",
                "location": "variables",
                "description": "Add safety interlock variable"
            },
            "add_fault_handling": {
                "condition": lambda code: "fault" not in code.lower(),
                "fix": "system_fault : BOOL := FALSE;",
                "location": "variables",
                "description": "Add fault handling variable"
            }
        }
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the debugger agent."""
        return """
You are a PLC Code Debugger Agent specialized in identifying and fixing code issues in IEC 61131-3 programs.

Your responsibilities:
1. Analyze validation errors and identify root causes
2. Provide automated fixes for common syntax and semantic errors
3. Suggest improvements for code quality and safety
4. Handle runtime errors and provide debugging strategies
5. Optimize code for better performance and maintainability
6. Ensure safety compliance through automated safety enhancements

Debugging approach:
1. Analyze the specific error or validation issue
2. Identify the root cause and affected code sections
3. Provide targeted fixes with explanations
4. Suggest preventive measures to avoid similar issues
5. Validate that fixes don't introduce new problems
6. Prioritize safety-critical fixes

Fix categories:
- SYNTAX: Basic language syntax errors
- SEMANTIC: Logic and type-related issues  
- SAFETY: Safety compliance and fail-safe behavior
- PERFORMANCE: Optimization and efficiency improvements
- STYLE: Code readability and maintainability

Always provide clear explanations for each fix and ensure all changes maintain or improve safety.
"""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a debugging task."""
        task_type = task.task_type
        input_data = task.input_data
        
        if task_type == "debug_failure":
            return await self._debug_failure(input_data)
        elif task_type == "fix_validation_errors":
            return await self._fix_validation_errors(input_data)
        elif task_type == "optimize_code":
            return await self._optimize_code(input_data)
        elif task_type == "enhance_safety":
            return await self._enhance_safety(input_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _debug_failure(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Debug a failed task and provide fixes."""
        failed_task = input_data.get("failed_task", {})
        workflow_context = input_data.get("workflow_context", {})
        
        task_error = failed_task.get("error", "")
        task_type = failed_task.get("task_type", "")
        
        # Analyze the failure
        failure_analysis = await self._analyze_failure(failed_task, workflow_context)
        
        # Generate fixes based on failure type
        suggested_fixes = []
        
        if "validation" in task_type.lower():
            # Handle validation failures
            validation_fixes = await self._generate_validation_fixes(failed_task, workflow_context)
            suggested_fixes.extend(validation_fixes)
        
        elif "generation" in task_type.lower():
            # Handle code generation failures
            generation_fixes = await self._generate_code_fixes(failed_task, workflow_context)
            suggested_fixes.extend(generation_fixes)
        
        elif "simulation" in task_type.lower():
            # Handle simulation failures
            simulation_fixes = await self._generate_simulation_fixes(failed_task, workflow_context)
            suggested_fixes.extend(simulation_fixes)
        
        else:
            # Generic fixes
            generic_fixes = await self._generate_generic_fixes(failed_task)
            suggested_fixes.extend(generic_fixes)
        
        return {
            "failure_analysis": failure_analysis,
            "suggested_fixes": suggested_fixes,
            "fix_priority": self._prioritize_fixes(suggested_fixes),
            "estimated_fix_time": sum(fix.get("estimated_time", 30) for fix in suggested_fixes),
            "debug_recommendations": self._generate_debug_recommendations(failure_analysis)
        }
    
    async def _fix_validation_errors(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fix validation errors in code."""
        validation_results = input_data.get("validation_results", [])
        code = input_data.get("code", "")
        
        fixed_code = code
        applied_fixes = []
        
        for validation_result in validation_results:
            issues = validation_result.get("issues", [])
            
            for issue in issues:
                if issue["severity"] == "error":
                    fix_result = await self._apply_fix_for_issue(fixed_code, issue)
                    if fix_result["success"]:
                        fixed_code = fix_result["fixed_code"]
                        applied_fixes.append(fix_result["fix_description"])
        
        return {
            "fixed_code": fixed_code,
            "applied_fixes": applied_fixes,
            "fix_count": len(applied_fixes),
            "success_rate": len(applied_fixes) / max(1, sum(len(vr.get("issues", [])) for vr in validation_results)) * 100
        }
    
    async def _optimize_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize code for better performance."""
        code = input_data.get("code", "")
        optimization_goals = input_data.get("goals", ["performance", "readability"])
        
        optimized_code = code
        optimizations_applied = []
        
        # Apply performance optimizations
        if "performance" in optimization_goals:
            perf_result = await self._apply_performance_optimizations(optimized_code)
            optimized_code = perf_result["code"]
            optimizations_applied.extend(perf_result["optimizations"])
        
        # Apply readability improvements
        if "readability" in optimization_goals:
            readability_result = await self._apply_readability_improvements(optimized_code)
            optimized_code = readability_result["code"]
            optimizations_applied.extend(readability_result["improvements"])
        
        # Apply safety enhancements
        if "safety" in optimization_goals:
            safety_result = await self._apply_safety_enhancements(optimized_code)
            optimized_code = safety_result["code"]
            optimizations_applied.extend(safety_result["enhancements"])
        
        return {
            "optimized_code": optimized_code,
            "optimizations_applied": optimizations_applied,
            "optimization_score": len(optimizations_applied) * 10,
            "before_metrics": self._calculate_code_metrics(code),
            "after_metrics": self._calculate_code_metrics(optimized_code)
        }
    
    async def _enhance_safety(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance safety features in code."""
        code = input_data.get("code", "")
        safety_level = input_data.get("safety_level", 1)
        
        enhanced_code = code
        safety_enhancements = []
        
        # Apply safety fixes based on SIL level
        for fix_name, fix_config in self.safety_fixes.items():
            if fix_config["condition"](enhanced_code):
                enhanced_code = await self._apply_safety_fix(enhanced_code, fix_config)
                safety_enhancements.append({
                    "name": fix_name,
                    "description": fix_config["description"],
                    "sil_level": safety_level
                })
        
        # Add safety-specific logic based on SIL level
        if safety_level >= 2:
            dual_channel_code = await self._add_dual_channel_logic(enhanced_code)
            if dual_channel_code != enhanced_code:
                enhanced_code = dual_channel_code
                safety_enhancements.append({
                    "name": "dual_channel_architecture",
                    "description": "Added dual channel safety architecture",
                    "sil_level": 2
                })
        
        if safety_level >= 3:
            redundancy_code = await self._add_redundancy_logic(enhanced_code)
            if redundancy_code != enhanced_code:
                enhanced_code = redundancy_code
                safety_enhancements.append({
                    "name": "triple_modular_redundancy",
                    "description": "Added triple modular redundancy",
                    "sil_level": 3
                })
        
        return {
            "enhanced_code": enhanced_code,
            "safety_enhancements": safety_enhancements,
            "safety_score": len(safety_enhancements) * 20,
            "compliance_level": f"SIL {safety_level}"
        }
    
    async def _analyze_failure(self, failed_task: Dict, workflow_context: Dict) -> Dict[str, Any]:
        """Analyze the root cause of a task failure."""
        error_message = failed_task.get("error", "")
        task_type = failed_task.get("task_type", "")
        
        analysis = {
            "error_category": self._categorize_error(error_message),
            "root_cause": self._identify_root_cause(error_message, task_type),
            "affected_components": self._identify_affected_components(failed_task, workflow_context),
            "severity": self._assess_error_severity(error_message),
            "recovery_strategy": self._determine_recovery_strategy(error_message, task_type)
        }
        
        return analysis
    
    async def _apply_fix_for_issue(self, code: str, issue: Dict) -> Dict[str, Any]:
        """Apply a specific fix for a validation issue."""
        issue_type = issue.get("type", "")
        issue_message = issue.get("message", "")
        line_number = issue.get("line", 0)
        
        # Try to match against known error patterns
        for pattern_name, pattern_config in self.error_patterns.items():
            if pattern_name in issue_type or any(keyword in issue_message.lower() 
                                               for keyword in pattern_name.split("_")):
                
                fixed_code = await self._apply_pattern_fix(code, pattern_config, line_number)
                if fixed_code != code:
                    return {
                        "success": True,
                        "fixed_code": fixed_code,
                        "fix_description": f"Applied {pattern_name} fix: {pattern_config['description']}"
                    }
        
        # If no pattern match, try generic fixes
        generic_fix = await self._apply_generic_fix(code, issue)
        return generic_fix
    
    async def _apply_pattern_fix(self, code: str, pattern_config: Dict, line_number: int) -> str:
        """Apply a pattern-based fix to code."""
        pattern = pattern_config["pattern"]
        fix = pattern_config["fix"]
        
        if line_number > 0:
            # Fix specific line
            lines = code.split('\n')
            if line_number <= len(lines):
                line = lines[line_number - 1]
                if callable(fix):
                    match = re.search(pattern, line)
                    if match:
                        lines[line_number - 1] = fix(match)
                else:
                    lines[line_number - 1] = re.sub(pattern, fix, line)
                return '\n'.join(lines)
        else:
            # Fix entire code
            if callable(fix):
                def replace_func(match):
                    return fix(match)
                return re.sub(pattern, replace_func, code)
            else:
                return re.sub(pattern, fix, code)
        
        return code
    
    async def _apply_generic_fix(self, code: str, issue: Dict) -> Dict[str, Any]:
        """Apply a generic fix based on issue description."""
        issue_message = issue.get("message", "").lower()
        
        if "semicolon" in issue_message:
            # Add missing semicolon
            line_number = issue.get("line", 0)
            if line_number > 0:
                lines = code.split('\n')
                if line_number <= len(lines):
                    line = lines[line_number - 1].rstrip()
                    if not line.endswith(';'):
                        lines[line_number - 1] = line + ';'
                        return {
                            "success": True,
                            "fixed_code": '\n'.join(lines),
                            "fix_description": "Added missing semicolon"
                        }
        
        elif "undeclared" in issue_message:
            # Add variable declaration
            var_match = re.search(r"'(\w+)'", issue_message)
            if var_match:
                var_name = var_match.group(1)
                # Insert variable declaration
                var_section = self._find_var_section(code)
                if var_section:
                    declaration = f"    {var_name} : BOOL := FALSE;"
                    fixed_code = code.replace(var_section, var_section + '\n' + declaration)
                    return {
                        "success": True,
                        "fixed_code": fixed_code,
                        "fix_description": f"Added declaration for variable '{var_name}'"
                    }
        
        return {
            "success": False,
            "fixed_code": code,
            "fix_description": "No applicable fix found"
        }
    
    async def _apply_performance_optimizations(self, code: str) -> Dict[str, Any]:
        """Apply performance optimizations to code."""
        optimized_code = code
        optimizations = []
        
        # Remove double negations
        double_neg_pattern = r'NOT\s+NOT\s+(\w+)'
        if re.search(double_neg_pattern, optimized_code):
            optimized_code = re.sub(double_neg_pattern, r'\1', optimized_code)
            optimizations.append("Removed double negations")
        
        # Simplify boolean expressions
        bool_true_pattern = r'(\w+)\s*=\s*TRUE'
        if re.search(bool_true_pattern, optimized_code):
            optimized_code = re.sub(bool_true_pattern, r'\1', optimized_code)
            optimizations.append("Simplified boolean expressions")
        
        # Optimize redundant comparisons
        redundant_pattern = r'(\w+)\s*=\s*FALSE'
        if re.search(redundant_pattern, optimized_code):
            optimized_code = re.sub(redundant_pattern, r'NOT \1', optimized_code)
            optimizations.append("Optimized boolean comparisons")
        
        return {
            "code": optimized_code,
            "optimizations": optimizations
        }
    
    async def _apply_readability_improvements(self, code: str) -> Dict[str, Any]:
        """Apply readability improvements to code."""
        improved_code = code
        improvements = []
        
        # Add comments for complex expressions
        lines = improved_code.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped and not stripped.startswith('//') and 
                (stripped.count('AND') + stripped.count('OR') > 2)):
                # Add comment before complex boolean expressions
                if i == 0 or not lines[i-1].strip().startswith('//'):
                    lines.insert(i, '    // Complex boolean logic')
                    improvements.append("Added comments for complex expressions")
                    break
        
        improved_code = '\n'.join(lines)
        
        # Improve variable naming (basic example)
        if 'temp' in improved_code and 'temperature' not in improved_code:
            improved_code = improved_code.replace('temp', 'temperature')
            improvements.append("Improved variable naming")
        
        return {
            "code": improved_code,
            "improvements": improvements
        }
    
    async def _apply_safety_enhancements(self, code: str) -> Dict[str, Any]:
        """Apply safety enhancements to code."""
        enhanced_code = code
        enhancements = []
        
        # Add safety checks to critical operations
        lines = enhanced_code.split('\n')
        for i, line in enumerate(lines):
            if ':=' in line and any(keyword in line.lower() for keyword in ['motor', 'valve', 'pump']):
                var_name = line.split(':=')[0].strip()
                # Add safety check
                safety_check = f"    {var_name} := {var_name} AND safety_ok;"
                if i + 1 < len(lines):
                    lines.insert(i + 1, safety_check)
                else:
                    lines.append(safety_check)
                enhancements.append(f"Added safety check for {var_name}")
                break
        
        enhanced_code = '\n'.join(lines)
        
        return {
            "code": enhanced_code,
            "enhancements": enhancements
        }
    
    async def _apply_safety_fix(self, code: str, fix_config: Dict) -> str:
        """Apply a specific safety fix to code."""
        fix_code = fix_config["fix"]
        location = fix_config["location"]
        
        if location == "variables":
            # Add to variable section
            var_section_end = code.find("END_VAR")
            if var_section_end != -1:
                insertion_point = var_section_end
                return code[:insertion_point] + f"    {fix_code}\n" + code[insertion_point:]
        
        return code
    
    async def _add_dual_channel_logic(self, code: str) -> str:
        """Add dual channel safety logic."""
        if "channel_a" not in code.lower():
            # Add dual channel variables and logic
            dual_channel_vars = """    channel_a_ok : BOOL := TRUE;
    channel_b_ok : BOOL := TRUE;
    channels_agree : BOOL := TRUE;"""
            
            var_section_end = code.find("END_VAR")
            if var_section_end != -1:
                code = code[:var_section_end] + dual_channel_vars + "\n" + code[var_section_end:]
            
            # Add comparison logic
            comparison_logic = """
// Dual channel comparison
channels_agree := channel_a_ok = channel_b_ok;
safety_ok := safety_ok AND channels_agree;"""
            
            return code + comparison_logic
        
        return code
    
    async def _add_redundancy_logic(self, code: str) -> str:
        """Add triple modular redundancy logic."""
        if "vote" not in code.lower():
            # Add voting logic for triple redundancy
            voting_vars = """    channel_c_ok : BOOL := TRUE;
    vote_result : BOOL := TRUE;"""
            
            var_section_end = code.find("END_VAR")
            if var_section_end != -1:
                code = code[:var_section_end] + voting_vars + "\n" + code[var_section_end:]
            
            # Add 2-out-of-3 voting logic
            voting_logic = """
// Triple modular redundancy with 2-out-of-3 voting
vote_result := (channel_a_ok AND channel_b_ok) OR 
               (channel_a_ok AND channel_c_ok) OR 
               (channel_b_ok AND channel_c_ok);
safety_ok := safety_ok AND vote_result;"""
            
            return code + voting_logic
        
        return code
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize the type of error."""
        error_lower = error_message.lower()
        
        if any(keyword in error_lower for keyword in ["syntax", "parse", "semicolon"]):
            return "syntax_error"
        elif any(keyword in error_lower for keyword in ["type", "undeclared", "undefined"]):
            return "semantic_error"
        elif any(keyword in error_lower for keyword in ["timeout", "connection", "network"]):
            return "runtime_error"
        elif any(keyword in error_lower for keyword in ["safety", "sil", "emergency"]):
            return "safety_error"
        else:
            return "unknown_error"
    
    def _identify_root_cause(self, error_message: str, task_type: str) -> str:
        """Identify the root cause of the error."""
        if "validation" in task_type and "syntax" in error_message.lower():
            return "Code generation produced syntactically incorrect output"
        elif "simulation" in task_type and "timeout" in error_message.lower():
            return "Simulation environment not responding or code has infinite loop"
        elif "undeclared" in error_message.lower():
            return "Variable used without proper declaration"
        else:
            return "Unknown root cause - requires manual investigation"
    
    def _identify_affected_components(self, failed_task: Dict, workflow_context: Dict) -> List[str]:
        """Identify which components are affected by the failure."""
        components = []
        
        task_type = failed_task.get("task_type", "")
        if "validation" in task_type:
            components.append("code_validator")
        elif "generation" in task_type:
            components.append("code_generator")
        elif "simulation" in task_type:
            components.append("simulator")
        
        return components
    
    def _assess_error_severity(self, error_message: str) -> str:
        """Assess the severity of the error."""
        error_lower = error_message.lower()
        
        if any(keyword in error_lower for keyword in ["safety", "emergency", "critical"]):
            return "critical"
        elif any(keyword in error_lower for keyword in ["syntax", "semantic", "validation"]):
            return "high"
        elif any(keyword in error_lower for keyword in ["performance", "optimization"]):
            return "medium"
        else:
            return "low"
    
    def _determine_recovery_strategy(self, error_message: str, task_type: str) -> str:
        """Determine the best recovery strategy."""
        if "syntax" in error_message.lower():
            return "apply_syntax_fixes"
        elif "validation" in task_type:
            return "fix_validation_errors"
        elif "timeout" in error_message.lower():
            return "optimize_and_retry"
        else:
            return "manual_intervention_required"
    
    def _prioritize_fixes(self, fixes: List[Dict]) -> List[Dict]:
        """Prioritize fixes based on severity and impact."""
        priority_order = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        
        return sorted(fixes, key=lambda fix: (
            priority_order.get(fix.get("severity", "low"), 4),
            -fix.get("impact_score", 0)
        ))
    
    def _generate_debug_recommendations(self, failure_analysis: Dict) -> List[str]:
        """Generate debugging recommendations."""
        recommendations = []
        
        error_category = failure_analysis.get("error_category", "")
        severity = failure_analysis.get("severity", "")
        
        if error_category == "syntax_error":
            recommendations.append("Review IEC 61131-3 syntax rules")
            recommendations.append("Use syntax validation tools during development")
        
        if error_category == "safety_error":
            recommendations.append("Conduct thorough safety analysis")
            recommendations.append("Implement additional safety measures")
        
        if severity == "critical":
            recommendations.append("Halt deployment until issue is resolved")
            recommendations.append("Escalate to safety engineer for review")
        
        return recommendations
    
    def _find_var_section(self, code: str) -> Optional[str]:
        """Find the VAR section in code."""
        var_match = re.search(r'VAR\s+.*?END_VAR', code, re.DOTALL)
        return var_match.group(0) if var_match else None
    
    def _calculate_code_metrics(self, code: str) -> Dict[str, int]:
        """Calculate basic code metrics."""
        lines = code.split('\n')
        
        return {
            "total_lines": len(lines),
            "code_lines": len([line for line in lines if line.strip() and not line.strip().startswith('//')]),
            "comment_lines": len([line for line in lines if line.strip().startswith('//')]),
            "variable_count": len(re.findall(r'(\w+)\s*:', code)),
            "complexity_score": code.count('IF') + code.count('CASE') + code.count('FOR') + code.count('WHILE')
        }
    
    async def _generate_validation_fixes(self, failed_task: Dict, workflow_context: Dict) -> List[Dict]:
        """Generate fixes for validation failures."""
        return [
            {
                "type": "validation_fix",
                "description": "Apply automated syntax corrections",
                "estimated_time": 60,
                "severity": "high",
                "impact_score": 80
            }
        ]
    
    async def _generate_code_fixes(self, failed_task: Dict, workflow_context: Dict) -> List[Dict]:
        """Generate fixes for code generation failures."""
        return [
            {
                "type": "generation_fix",
                "description": "Regenerate code with improved templates",
                "estimated_time": 120,
                "severity": "medium",
                "impact_score": 70
            }
        ]
    
    async def _generate_simulation_fixes(self, failed_task: Dict, workflow_context: Dict) -> List[Dict]:
        """Generate fixes for simulation failures."""
        return [
            {
                "type": "simulation_fix",
                "description": "Optimize code for simulation environment",
                "estimated_time": 90,
                "severity": "medium",
                "impact_score": 60
            }
        ]
    
    async def _generate_generic_fixes(self, failed_task: Dict) -> List[Dict]:
        """Generate generic fixes for unknown failures."""
        return [
            {
                "type": "generic_fix",
                "description": "Retry task with increased timeout",
                "estimated_time": 30,
                "severity": "low",
                "impact_score": 40
            }
        ]
