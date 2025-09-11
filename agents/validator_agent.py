"""Validator agent for PLC code syntax and semantic validation."""

import logging
import re
from typing import Dict, Any, List, Tuple
from datetime import datetime

from agents.base_agent import LLMAgent
from models.schemas import AgentRole, AgentTask, ValidationResult, ValidationLevel


class ValidatorAgent(LLMAgent):
    """Agent responsible for validating PLC code syntax, semantics, and safety compliance."""
    
    def __init__(self, llm=None):
        super().__init__(
            role=AgentRole.VALIDATOR,
            name="PLC Code Validator",
            description="Validates PLC code for syntax, semantics, and safety compliance",
            llm=llm
        )
        
        # IEC 61131-3 keywords and data types
        self.st_keywords = {
            'control_flow': ['IF', 'THEN', 'ELSE', 'ELSIF', 'END_IF', 'CASE', 'OF', 'END_CASE',
                           'FOR', 'TO', 'BY', 'DO', 'END_FOR', 'WHILE', 'END_WHILE',
                           'REPEAT', 'UNTIL', 'END_REPEAT', 'EXIT', 'RETURN'],
            'data_types': ['BOOL', 'SINT', 'INT', 'DINT', 'LINT', 'USINT', 'UINT', 'UDINT', 'ULINT',
                          'REAL', 'LREAL', 'TIME', 'DATE', 'TIME_OF_DAY', 'DATE_AND_TIME',
                          'STRING', 'WSTRING', 'BYTE', 'WORD', 'DWORD', 'LWORD'],
            'operators': ['AND', 'OR', 'XOR', 'NOT', 'MOD', 'ABS', 'SQRT', 'LN', 'LOG', 'EXP',
                         'SIN', 'COS', 'TAN', 'ASIN', 'ACOS', 'ATAN', 'LIMIT', 'MAX', 'MIN'],
            'declarations': ['VAR', 'VAR_INPUT', 'VAR_OUTPUT', 'VAR_IN_OUT', 'VAR_TEMP', 'VAR_GLOBAL',
                           'VAR_ACCESS', 'VAR_EXTERNAL', 'END_VAR', 'CONSTANT', 'RETAIN', 'NON_RETAIN'],
            'program_units': ['PROGRAM', 'END_PROGRAM', 'FUNCTION', 'END_FUNCTION',
                            'FUNCTION_BLOCK', 'END_FUNCTION_BLOCK', 'TYPE', 'END_TYPE']
        }
        
        # Common function blocks
        self.standard_fbs = ['TON', 'TOF', 'TP', 'CTU', 'CTD', 'CTUD', 'R_TRIG', 'F_TRIG', 'SR', 'RS']
        
        # Safety validation rules
        self.safety_rules = {
            'sil_1': ['basic_fault_detection', 'simple_diagnostics'],
            'sil_2': ['dual_channel', 'comparison_monitoring', 'test_pulse'],
            'sil_3': ['triple_modular_redundancy', 'diverse_technology', 'proof_testing'],
            'sil_4': ['quadruple_redundancy', 'formal_verification', 'diverse_implementation']
        }
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the validator agent."""
        return """
You are a PLC Code Validator Agent specialized in IEC 61131-3 compliance and safety validation.

Your responsibilities:
1. Validate Structured Text (ST) syntax according to IEC 61131-3 standards
2. Perform semantic analysis to ensure logical correctness
3. Check safety compliance based on Safety Integrity Level (SIL) requirements
4. Identify potential runtime errors and performance issues
5. Verify proper use of data types and variable scoping
6. Validate function block usage and parameter passing

Validation levels:
- SYNTAX: Check language syntax and structure
- SEMANTIC: Validate logic flow and data consistency
- SAFETY: Ensure safety requirements are met
- PERFORMANCE: Check for optimization opportunities
- COMPLIANCE: Verify IEC 61131-3 standard compliance

Safety validation criteria:
- SIL 1: Basic fault detection and simple diagnostics
- SIL 2: Dual channel architecture with comparison
- SIL 3: Triple modular redundancy with voting
- SIL 4: Quadruple redundancy with formal verification

Always provide detailed feedback with specific line numbers and actionable recommendations.
"""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a validation task."""
        task_type = task.task_type
        input_data = task.input_data
        
        if task_type == "validate_code":
            return await self._validate_code(input_data)
        elif task_type == "syntax_check":
            return await self._syntax_check(input_data)
        elif task_type == "semantic_check":
            return await self._semantic_check(input_data)
        elif task_type == "safety_check":
            return await self._safety_check(input_data)
        elif task_type == "performance_check":
            return await self._performance_check(input_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _validate_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive code validation."""
        generated_code_data = input_data.get("previous_results", {}).get("generate_code", {})
        requirement = input_data.get("requirement", {})
        
        if not generated_code_data:
            raise ValueError("No generated code found for validation")
        
        generated_code_obj = generated_code_data.get("generated_code", {})
        code = generated_code_obj.get("code", "")
        safety_level = requirement.get("safety_level", 1)
        
        validation_results = []
        
        # 1. Syntax validation
        syntax_result = await self._perform_syntax_validation(code)
        validation_results.append(syntax_result)
        
        # 2. Semantic validation
        semantic_result = await self._perform_semantic_validation(code, requirement)
        validation_results.append(semantic_result)
        
        # 3. Safety validation (if SIL > 1)
        if safety_level > 1:
            safety_result = await self._perform_safety_validation(code, safety_level)
            validation_results.append(safety_result)
        
        # 4. Performance validation
        performance_result = await self._perform_performance_validation(code)
        validation_results.append(performance_result)
        
        # 5. Compliance validation
        compliance_result = await self._perform_compliance_validation(code)
        validation_results.append(compliance_result)
        
        # Calculate overall validation score
        total_issues = sum(len(result["issues"]) for result in validation_results)
        overall_passed = all(result["passed"] for result in validation_results)
        
        return {
            "validation_results": validation_results,
            "overall_passed": overall_passed,
            "total_issues": total_issues,
            "validation_score": max(0, 100 - (total_issues * 10)),
            "recommendations": self._generate_recommendations(validation_results),
            "validated_at": datetime.utcnow().isoformat()
        }
    
    async def _syntax_check(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform syntax validation only."""
        code = input_data.get("code", "")
        return await self._perform_syntax_validation(code)
    
    async def _semantic_check(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform semantic validation only."""
        code = input_data.get("code", "")
        requirement = input_data.get("requirement", {})
        return await self._perform_semantic_validation(code, requirement)
    
    async def _safety_check(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform safety validation only."""
        code = input_data.get("code", "")
        safety_level = input_data.get("safety_level", 1)
        return await self._perform_safety_validation(code, safety_level)
    
    async def _performance_check(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform performance validation only."""
        code = input_data.get("code", "")
        return await self._perform_performance_validation(code)
    
    async def _perform_syntax_validation(self, code: str) -> Dict[str, Any]:
        """Validate code syntax according to IEC 61131-3."""
        issues = []
        lines = code.split('\n')
        
        # Check for basic syntax issues
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('//'):
                continue
            
            # Check for missing semicolons
            if (line_stripped.endswith(':=') or 
                (any(op in line_stripped for op in [':=', 'IF', 'THEN']) and 
                 not line_stripped.endswith(';') and 
                 not any(kw in line_stripped for kw in ['THEN', 'DO', 'OF']))):
                issues.append({
                    "line": i,
                    "type": "syntax_error",
                    "message": "Missing semicolon at end of statement",
                    "severity": "error"
                })
            
            # Check for unmatched parentheses
            if line_stripped.count('(') != line_stripped.count(')'):
                issues.append({
                    "line": i,
                    "type": "syntax_error",
                    "message": "Unmatched parentheses",
                    "severity": "error"
                })
            
            # Check for invalid variable names
            var_assignments = re.findall(r'(\w+)\s*:=', line_stripped)
            for var_name in var_assignments:
                if var_name.upper() in [kw for kw_list in self.st_keywords.values() for kw in kw_list]:
                    issues.append({
                        "line": i,
                        "type": "syntax_error",
                        "message": f"Variable name '{var_name}' conflicts with reserved keyword",
                        "severity": "error"
                    })
        
        # Check for proper program structure
        if 'PROGRAM' in code and 'END_PROGRAM' not in code:
            issues.append({
                "line": 0,
                "type": "structure_error",
                "message": "PROGRAM block not properly closed with END_PROGRAM",
                "severity": "error"
            })
        
        # Check VAR blocks
        var_blocks = re.findall(r'VAR(?:_\w+)?\s+.*?END_VAR', code, re.DOTALL)
        for block in var_blocks:
            if block.count('VAR') != block.count('END_VAR'):
                issues.append({
                    "line": 0,
                    "type": "structure_error",
                    "message": "VAR block not properly closed",
                    "severity": "error"
                })
        
        return {
            "level": ValidationLevel.SYNTAX,
            "passed": len(issues) == 0,
            "issues": issues,
            "suggestions": self._generate_syntax_suggestions(issues)
        }
    
    async def _perform_semantic_validation(self, code: str, requirement: Dict[str, Any]) -> Dict[str, Any]:
        """Validate code semantics and logic."""
        issues = []
        
        # Extract variable declarations
        declared_vars = self._extract_variable_declarations(code)
        used_vars = self._extract_variable_usage(code)
        
        # Check for undeclared variables
        for var_name, line_num in used_vars:
            if var_name not in [var['name'] for var in declared_vars]:
                issues.append({
                    "line": line_num,
                    "type": "semantic_error",
                    "message": f"Variable '{var_name}' used but not declared",
                    "severity": "error"
                })
        
        # Check for unused variables
        used_var_names = set(var_name for var_name, _ in used_vars)
        for var in declared_vars:
            if var['name'] not in used_var_names:
                issues.append({
                    "line": var['line'],
                    "type": "semantic_warning",
                    "message": f"Variable '{var['name']}' declared but never used",
                    "severity": "warning"
                })
        
        # Check for type consistency
        type_issues = self._check_type_consistency(code, declared_vars)
        issues.extend(type_issues)
        
        # Check for infinite loops
        loop_issues = self._check_for_infinite_loops(code)
        issues.extend(loop_issues)
        
        # Check for unreachable code
        unreachable_issues = self._check_unreachable_code(code)
        issues.extend(unreachable_issues)
        
        return {
            "level": ValidationLevel.SEMANTIC,
            "passed": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
            "suggestions": self._generate_semantic_suggestions(issues)
        }
    
    async def _perform_safety_validation(self, code: str, safety_level: int) -> Dict[str, Any]:
        """Validate safety requirements based on SIL level."""
        issues = []
        
        # Check for emergency stop handling
        if "emergency_stop" not in code.lower():
            issues.append({
                "line": 0,
                "type": "safety_error",
                "message": "No emergency stop handling found",
                "severity": "error" if safety_level > 1 else "warning"
            })
        
        # Check for fault detection
        if "fault" not in code.lower():
            issues.append({
                "line": 0,
                "type": "safety_warning",
                "message": "No fault detection mechanisms found",
                "severity": "warning"
            })
        
        # Check for safety interlocks
        safety_patterns = ["safety_ok", "safety_enable", "safety_fault"]
        if not any(pattern in code.lower() for pattern in safety_patterns):
            issues.append({
                "line": 0,
                "type": "safety_error",
                "message": "No safety interlock patterns found",
                "severity": "error" if safety_level > 2 else "warning"
            })
        
        # SIL-specific checks
        if safety_level >= 2:
            # Check for dual channel architecture
            if not self._check_dual_channel(code):
                issues.append({
                    "line": 0,
                    "type": "safety_error",
                    "message": "SIL 2+ requires dual channel architecture",
                    "severity": "error"
                })
        
        if safety_level >= 3:
            # Check for triple modular redundancy
            if not self._check_redundancy(code, min_channels=3):
                issues.append({
                    "line": 0,
                    "type": "safety_error",
                    "message": "SIL 3+ requires triple modular redundancy",
                    "severity": "error"
                })
        
        return {
            "level": ValidationLevel.SAFETY,
            "passed": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
            "suggestions": self._generate_safety_suggestions(issues, safety_level)
        }
    
    async def _perform_performance_validation(self, code: str) -> Dict[str, Any]:
        """Validate code for performance issues."""
        issues = []
        lines = code.split('\n')
        
        # Check for inefficient patterns
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Check for redundant boolean operations
            if re.search(r'NOT\s+NOT\s+\w+', line_stripped):
                issues.append({
                    "line": i,
                    "type": "performance_warning",
                    "message": "Double negation can be simplified",
                    "severity": "warning"
                })
            
            # Check for complex expressions that could be simplified
            if line_stripped.count('AND') + line_stripped.count('OR') > 5:
                issues.append({
                    "line": i,
                    "type": "performance_warning",
                    "message": "Complex boolean expression - consider breaking into multiple statements",
                    "severity": "warning"
                })
        
        # Check for potential optimization opportunities
        if code.count('FOR') > 3:
            issues.append({
                "line": 0,
                "type": "performance_info",
                "message": "Multiple loops detected - consider optimization",
                "severity": "info"
            })
        
        return {
            "level": ValidationLevel.PERFORMANCE,
            "passed": True,  # Performance issues are warnings/info only
            "issues": issues,
            "suggestions": self._generate_performance_suggestions(issues)
        }
    
    async def _perform_compliance_validation(self, code: str) -> Dict[str, Any]:
        """Validate IEC 61131-3 compliance."""
        issues = []
        
        # Check for proper naming conventions
        var_names = re.findall(r'(\w+)\s*:', code)
        for var_name in var_names:
            if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', var_name):
                issues.append({
                    "line": 0,
                    "type": "compliance_warning",
                    "message": f"Variable name '{var_name}' doesn't follow IEC 61131-3 naming conventions",
                    "severity": "warning"
                })
        
        # Check for proper documentation
        comment_lines = len([line for line in code.split('\n') if line.strip().startswith('//')])
        code_lines = len([line for line in code.split('\n') if line.strip() and not line.strip().startswith('//')])
        
        if code_lines > 0 and comment_lines / code_lines < 0.1:
            issues.append({
                "line": 0,
                "type": "compliance_warning",
                "message": "Insufficient code documentation (less than 10% comment ratio)",
                "severity": "warning"
            })
        
        return {
            "level": ValidationLevel.COMPLIANCE,
            "passed": len([i for i in issues if i["severity"] == "error"]) == 0,
            "issues": issues,
            "suggestions": self._generate_compliance_suggestions(issues)
        }
    
    def _extract_variable_declarations(self, code: str) -> List[Dict[str, Any]]:
        """Extract variable declarations from code."""
        variables = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Match variable declarations
            match = re.match(r'\s*(\w+)\s*:\s*(\w+)(?:\s*:=\s*([^;]+))?;', line)
            if match:
                var_name, var_type, default_value = match.groups()
                variables.append({
                    "name": var_name,
                    "type": var_type,
                    "default_value": default_value.strip() if default_value else None,
                    "line": i
                })
        
        return variables
    
    def _extract_variable_usage(self, code: str) -> List[Tuple[str, int]]:
        """Extract variable usage from code."""
        usage = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Skip variable declarations and comments
            if ':' in line and ('VAR' in line or re.match(r'\s*\w+\s*:\s*\w+', line)):
                continue
            if line.strip().startswith('//'):
                continue
            
            # Find variable references
            var_refs = re.findall(r'\b([A-Za-z][A-Za-z0-9_]*)\b', line)
            for var_ref in var_refs:
                if var_ref.upper() not in [kw for kw_list in self.st_keywords.values() for kw in kw_list]:
                    usage.append((var_ref, i))
        
        return usage
    
    def _check_type_consistency(self, code: str, declared_vars: List[Dict]) -> List[Dict[str, Any]]:
        """Check for type consistency issues."""
        issues = []
        
        # Create type mapping
        var_types = {var['name']: var['type'] for var in declared_vars}
        
        # Check assignments
        assignments = re.findall(r'(\w+)\s*:=\s*([^;]+);', code)
        for var_name, value in assignments:
            if var_name in var_types:
                var_type = var_types[var_name]
                
                # Check boolean assignments
                if var_type == 'BOOL' and value.strip() not in ['TRUE', 'FALSE', '0', '1']:
                    if not any(op in value for op in ['AND', 'OR', 'NOT', '=', '<', '>']):
                        issues.append({
                            "line": 0,
                            "type": "type_error",
                            "message": f"Type mismatch: assigning non-boolean value to BOOL variable '{var_name}'",
                            "severity": "error"
                        })
        
        return issues
    
    def _check_for_infinite_loops(self, code: str) -> List[Dict[str, Any]]:
        """Check for potential infinite loops."""
        issues = []
        
        # Simple check for WHILE loops without obvious exit conditions
        while_loops = re.findall(r'WHILE\s+([^DO]+)\s+DO', code, re.IGNORECASE)
        for condition in while_loops:
            if 'TRUE' in condition.upper() and 'EXIT' not in code.upper():
                issues.append({
                    "line": 0,
                    "type": "logic_warning",
                    "message": "Potential infinite loop detected - no EXIT statement found",
                    "severity": "warning"
                })
        
        return issues
    
    def _check_unreachable_code(self, code: str) -> List[Dict[str, Any]]:
        """Check for unreachable code."""
        issues = []
        
        # Simple check for code after RETURN statements
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if 'RETURN' in line.upper() and i < len(lines) - 1:
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('//') and 'END_' not in next_line.upper():
                    issues.append({
                        "line": i + 2,
                        "type": "logic_warning",
                        "message": "Unreachable code after RETURN statement",
                        "severity": "warning"
                    })
        
        return issues
    
    def _check_dual_channel(self, code: str) -> bool:
        """Check for dual channel safety architecture."""
        # Look for patterns indicating dual channel implementation
        dual_patterns = ['channel_a', 'channel_b', 'ch1', 'ch2', 'primary', 'secondary']
        return any(pattern in code.lower() for pattern in dual_patterns)
    
    def _check_redundancy(self, code: str, min_channels: int) -> bool:
        """Check for redundancy implementation."""
        # Look for voting or comparison logic
        voting_patterns = ['vote', 'majority', 'compare', 'redundant']
        return any(pattern in code.lower() for pattern in voting_patterns)
    
    def _generate_recommendations(self, validation_results: List[Dict]) -> List[str]:
        """Generate overall recommendations based on validation results."""
        recommendations = []
        
        total_errors = sum(len([i for i in result["issues"] if i["severity"] == "error"]) 
                          for result in validation_results)
        
        if total_errors > 0:
            recommendations.append("Fix all syntax and semantic errors before deployment")
        
        safety_issues = [result for result in validation_results if result.get("level") == ValidationLevel.SAFETY]
        if safety_issues and any(not result["passed"] for result in safety_issues):
            recommendations.append("Address all safety-critical issues before deployment")
        
        performance_issues = sum(len(result["issues"]) for result in validation_results 
                               if result.get("level") == ValidationLevel.PERFORMANCE)
        if performance_issues > 3:
            recommendations.append("Consider optimizing code for better performance")
        
        return recommendations
    
    def _generate_syntax_suggestions(self, issues: List[Dict]) -> List[str]:
        """Generate syntax-specific suggestions."""
        suggestions = []
        
        if any(issue["type"] == "syntax_error" for issue in issues):
            suggestions.append("Review IEC 61131-3 syntax rules and fix all syntax errors")
        
        if any("semicolon" in issue["message"] for issue in issues):
            suggestions.append("Ensure all statements end with semicolons")
        
        return suggestions
    
    def _generate_semantic_suggestions(self, issues: List[Dict]) -> List[str]:
        """Generate semantic-specific suggestions."""
        suggestions = []
        
        if any("undeclared" in issue["message"] for issue in issues):
            suggestions.append("Declare all variables before use")
        
        if any("unused" in issue["message"] for issue in issues):
            suggestions.append("Remove unused variables to improve code clarity")
        
        return suggestions
    
    def _generate_safety_suggestions(self, issues: List[Dict], safety_level: int) -> List[str]:
        """Generate safety-specific suggestions."""
        suggestions = []
        
        suggestions.append(f"Ensure all SIL {safety_level} requirements are met")
        
        if any("emergency_stop" in issue["message"] for issue in issues):
            suggestions.append("Implement proper emergency stop handling")
        
        if safety_level >= 2:
            suggestions.append("Implement dual channel safety architecture")
        
        return suggestions
    
    def _generate_performance_suggestions(self, issues: List[Dict]) -> List[str]:
        """Generate performance-specific suggestions."""
        suggestions = []
        
        if any("complex" in issue["message"] for issue in issues):
            suggestions.append("Break complex expressions into simpler statements")
        
        if any("loop" in issue["message"] for issue in issues):
            suggestions.append("Optimize loop structures for better performance")
        
        return suggestions
    
    def _generate_compliance_suggestions(self, issues: List[Dict]) -> List[str]:
        """Generate compliance-specific suggestions."""
        suggestions = []
        
        if any("naming" in issue["message"] for issue in issues):
            suggestions.append("Follow IEC 61131-3 naming conventions")
        
        if any("documentation" in issue["message"] for issue in issues):
            suggestions.append("Add more comments and documentation")
        
        return suggestions
