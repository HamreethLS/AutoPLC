"""
Enhanced Validator Agent with comprehensive analysis and detailed reporting
"""

import json
import asyncio
import re
from typing import Dict, List, Optional, Any, Tuple

from backend.tools.compiler import run_iec2c_compiler
from backend.tools.linter import run_linter, get_linter_stats, validate_program_structure
from backend.utils.nim_client import enhanced_nim_client

class ValidationResult:
    def __init__(self, success: bool, score: float, details: Dict[str, Any]):
        self.success = success
        self.score = score
        self.details = details
        self.compilation_result = details.get("compilation", "")
        self.linter_result = details.get("linter", "")
        self.suggestions = details.get("suggestions", [])

class ValidatorAgent:
    """Enhanced validator with multi-tier validation and intelligent reporting"""
    
    def __init__(self):
        self.validation_weights = {
            "llm_validation": 0.4,
            "structure": 0.2,
            "style": 0.1,
            "safety": 0.2,
            "performance": 0.1
        }
    
    async def validate_code(self, code: str, knowledge_context: Optional[str] = None, plan: Optional[str] = None) -> str:
        """Comprehensive code validation with detailed reporting"""
        
        if not code or len(code.strip()) < 10:
            return "❌ Validation Failed: No code provided for validation"
        
        # Multi-tier validation
        validation_result = await self._run_comprehensive_validation(code, knowledge_context, plan)
        
        # Generate human-readable report
        return self._generate_validation_report(validation_result)

    def compile_code_only(self, code: str) -> str:
        """Runs only the MATIEC compiler on the given code."""
        if not code or len(code.strip()) < 10:
            return "No code provided to compile."
        
        compilation_result = run_iec2c_compiler(code)
        return compilation_result

    async def _run_comprehensive_validation(self, code: str, knowledge_context: Optional[str] = None, plan: Optional[str] = None) -> ValidationResult:
        """Run all validation tiers"""
        
        details = {}
        scores = {}
        
        # Tier 1: Pre-compilation syntax validation
        syntax_validation = validate_program_structure(code)
        details["syntax"] = syntax_validation
        scores["structure"] = 1.0 if syntax_validation["valid"] else 0.3

        # Tier 2: Advanced linting
        linter_result = run_linter(code)
        details["linter"] = linter_result
        scores["style"] = self._calculate_linter_score(linter_result)

        # Tier 3: LLM-based validation
        llm_has_issues = False
        if knowledge_context or plan:
            llm_validation_result = await self._validate_with_llm(code, knowledge_context, plan)
            details["llm_validation"] = llm_validation_result
            scores["llm_validation"] = llm_validation_result["score"]
            # Check if the LLM reported any issues
            report = llm_validation_result.get("report", {})
            if report.get("issues") and len(report.get("issues")) > 0:
                llm_has_issues = True
        else:
            # If no context, we can't do LLM validation. Give a neutral score.
            scores["llm_validation"] = 0.6
        
        # Tier 4: Safety analysis
        safety_analysis = self._analyze_safety_patterns(code)
        details["safety"] = safety_analysis
        scores["safety"] = safety_analysis["score"]
        
        # Tier 5: Performance analysis
        performance_analysis = self._analyze_performance(code)
        details["performance"] = performance_analysis
        scores["performance"] = performance_analysis["score"]
        
        # Tier 6: Code statistics
        stats = get_linter_stats(code)
        details["statistics"] = stats
        
        # Calculate overall score
        total_weight = sum(self.validation_weights.get(cat, 0) for cat in scores)
        overall_score = sum(
            scores[category] * self.validation_weights.get(category, 0)
            for category in scores
        ) / total_weight if total_weight > 0 else 0
        
        llm_score = scores.get("llm_validation", 0.0)

        # Determine success
        # Success is determined by a high overall score, with a minimum bar for structure.
        success = (
            overall_score > 0.6 and
            scores.get("structure", 0) > 0.5 # Ensures basic program structure is valid
        )
        
        return ValidationResult(success, overall_score, details)
    
    async def _validate_with_llm(self, code: str, knowledge_context: Optional[str], plan: Optional[str]) -> Dict[str, Any]:
        """Use an LLM to validate the code against provided knowledge."""
        prompt = f"""
You are an expert IEC 61131-3 and MATIEC syntax and logic validator.
Your task is to perform a two-part analysis of the provided Structured Text code.

**Part 1: Logical Correctness Analysis**
- **Goal:** Does the code's logic perfectly implement the user's plan?
- **User's Plan:**
---
{plan or "No plan provided."}
---

**Part 2: Syntax and Compliance Analysis**
- **Goal:** Does the code adhere to the syntax rules and best practices from the knowledge context?
- **Knowledge Context:**
---
{knowledge_context or "No specific knowledge context provided."}
---

**Structured Text Code to Validate:**
---
```st
{code}
```
---

**Instructions:**
1.  **Logical Review:** First, meticulously compare the code's behavior against the user's plan. Identify any logical errors, missing features, or incorrect implementations.
2.  **Syntax & Compliance Review:** Second, check if the code strictly follows the rules from the knowledge context.
3.  **Identify All Issues:** List any deviations, logical errors, or potential problems from both analyses.
4.  **Provide a Score:** Give a compliance score from 0.0 to 1.0. The score should be 1.0 ONLY if the logic is a 100% perfect match for the plan AND there are zero syntax/compliance issues.
5.  **Generate Corrections:** Provide clear, actionable suggestions for the Coder agent to fix all identified issues.

**Output Format (JSON only):**
{{
  "compliance_score": <float between 0.0 and 1.0>,
  "issues": [
    "Issue 1: Description of the problem and why it violates the context.",
    "Issue 2: Another problem found."
  ],
  "correction_guide": "A summary of instructions for the Coder agent to fix the code. Be very specific."
}}
"""
        try:
            response_str = await enhanced_nim_client.call_agent_simple(
                agent_role="validator",
                prompt=prompt,
                temperature=0.0,
                max_tokens=1024
            )
            
            # More robust JSON extraction
            json_str = response_str
            json_match = re.search(r"```json\s*([\s\S]+?)\s*```", response_str)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Fallback for raw JSON, find first '{' and last '}'
                start = response_str.find('{')
                end = response_str.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = response_str[start:end+1]

            result = json.loads(json_str)
            return {"score": result.get("compliance_score", 0.5), "report": result}
        except json.JSONDecodeError as e:
            return {"score": 0.2, "report": {"error": f"LLM returned invalid JSON: {e}", "issues": ["The validation model produced a malformed response."], "correction_guide": "Could not perform LLM-based validation due to a response format error."}}
        except Exception as e: # Catch other potential errors
            return {"score": 0.3, "report": {"error": f"LLM validation failed unexpectedly: {e}", "issues": [], "correction_guide": "Could not perform LLM-based validation."}}

    def _calculate_linter_score(self, linter_result: str) -> float:
        """Calculate score from linter results"""
        
        if "passed" in linter_result.lower():
            return 1.0
        elif "warnings found" in linter_result.lower():
            # Count warnings to determine severity
            warning_count = linter_result.lower().count("warning")
            return max(0.4, 1.0 - (warning_count * 0.1))
        elif "errors found" in linter_result.lower():
            return 0.2
        else:
            return 0.5
    
    def _analyze_safety_patterns(self, code: str) -> Dict[str, Any]:
        """Analyze code for safety patterns and concerns"""
        
        safety_score = 0.5  # Default neutral score
        issues = []
        good_patterns = []
        
        code_lower = code.lower()
        
        # Check for emergency stop patterns
        if any(pattern in code_lower for pattern in ['emergency', 'e_stop', 'estop']):
            good_patterns.append("Emergency stop logic detected")
            safety_score += 0.2
        
        # Check for safety interlocks
        if any(pattern in code_lower for pattern in ['interlock', 'safety', 'fail_safe']):
            good_patterns.append("Safety interlock patterns found")
            safety_score += 0.1
        
        # Check for input validation
        if re.search(r'IF\s+.*\s+AND\s+.*\s+THEN', code, re.IGNORECASE):
            good_patterns.append("Input validation patterns detected")
            safety_score += 0.1
        
        # Check for dangerous patterns
        if re.search(r'\b(WHILE|FOR|REPEAT)\b', code, re.IGNORECASE):
            issues.append("WARNING: Loop constructs may cause scan cycle issues")
            safety_score -= 0.2
        
        # Check for unprotected outputs
        output_assignments = re.findall(r'(\w+)\s*:=\s*TRUE', code, re.IGNORECASE)
        if len(output_assignments) > 0 and not any(word in code_lower for word in ['stop', 'safety', 'emergency']):
            issues.append("Consider adding safety interlocks for output activations")
            safety_score -= 0.1
        
        return {
            "score": max(0.0, min(1.0, safety_score)),
            "good_patterns": good_patterns,
            "issues": issues
        }
    
    def _analyze_performance(self, code: str) -> Dict[str, Any]:
        """Analyze code for performance characteristics"""
        
        performance_score = 0.7  # Start with good baseline
        recommendations = []
        
        # Check code complexity
        lines = code.split('\n')
        code_lines = [line for line in lines if line.strip() and not line.strip().startswith('(*')]
        
        if len(code_lines) > 100:
            performance_score -= 0.1
            recommendations.append("Consider breaking down large programs into smaller functions")
        
        # Check nesting depth
        max_nesting = 0
        current_nesting = 0
        for line in lines:
            stripped = line.strip().upper()
            if any(stripped.startswith(kw) for kw in ['IF', 'CASE']):
                current_nesting += 1
                max_nesting = max(max_nesting, current_nesting)
            elif any(stripped.startswith(kw) for kw in ['END_IF', 'END_CASE']):
                current_nesting = max(0, current_nesting - 1)
        
        if max_nesting > 3:
            performance_score -= 0.2
            recommendations.append(f"Deep nesting ({max_nesting} levels) may impact readability and performance")
        
        # Check for redundant calculations
        assignments = re.findall(r'(\w+)\s*:=\s*(.+)', code)
        expressions = [expr.strip() for _, expr in assignments]
        duplicates = [expr for expr in set(expressions) if expressions.count(expr) > 1]
        
        if duplicates:
            performance_score -= 0.1
            recommendations.append("Consider using intermediate variables for repeated calculations")
        
        return {
            "score": max(0.0, min(1.0, performance_score)),
            "complexity_metrics": {
                "code_lines": len(code_lines),
                "max_nesting": max_nesting,
                "duplicate_expressions": len(duplicates)
            },
            "recommendations": recommendations
        }
    
    def _generate_validation_report(self, result: ValidationResult) -> str:
        """Generate a comprehensive human-readable validation report"""
        
        status_emoji = "✅" if result.success else "❌"
        status_text = "VALIDATION PASSED" if result.success else "VALIDATION FAILED"
        
        report_lines = [
            f"{status_emoji} {status_text}",
            f"Overall Quality Score: {result.score:.1f}/1.0",
            "=" * 50
        ]
        
        # Compilation results
        # Compilation is now optional and handled separately.
        # We can add a note about it.
        report_lines.append("🔧 COMPILATION: (On-demand) Use the 'Compile' button to check with MATIEC.")
        
        # Syntax validation
        syntax = result.details.get("syntax", {})
        if syntax.get("valid", False):
            report_lines.append("📝 SYNTAX: ✅ Valid IEC 61131-3 structure")
        else:
            report_lines.append("📝 SYNTAX: ❌ Structure issues found")
            for issue in syntax.get("errors", []):
                report_lines.append(f"   • {issue}")
        
        # Linter results
        linter = result.details.get("linter", "")
        if "passed" in linter.lower():
            report_lines.append("🔍 LINTER: ✅ Code style and quality checks passed")
        else:
            report_lines.append("🔍 LINTER: ⚠️ Issues found")
            # Extract key issues from linter output
            if "warnings" in linter.lower():
                report_lines.append("   See detailed linter output for specific warnings")

        # LLM Validation
        llm_validation = result.details.get("llm_validation")
        if llm_validation:
            report = llm_validation.get("report", {})
            score = llm_validation.get("score", 0.5)
            if report.get("error"):
                report_lines.append("🧠 LLM VALIDATION: ❌ Error")
                report_lines.append(f"   • {report['error']}")
            elif score > 0.8:
                report_lines.append("🧠 LLM VALIDATION: ✅ Compliant with provided knowledge")
            else:
                report_lines.append("🧠 LLM VALIDATION: ⚠️ Issues found against knowledge context")
                for issue in report.get("issues", []):
                    report_lines.append(f"   • {issue}")
        
        # Safety analysis
        safety = result.details.get("safety", {})
        safety_score = safety.get("score", 0.5)
        if safety_score > 0.7:
            report_lines.append("🛡️ SAFETY: ✅ Good safety patterns detected")
        elif safety_score > 0.4:
            report_lines.append("🛡️ SAFETY: ⚠️ Consider additional safety measures")
        else:
            report_lines.append("🛡️ SAFETY: ❌ Safety concerns identified")
        
        for pattern in safety.get("good_patterns", []):
            report_lines.append(f"   ✅ {pattern}")
        for issue in safety.get("issues", []):
            report_lines.append(f"   ⚠️ {issue}")
        
        # Performance analysis
        performance = result.details.get("performance", {})
        perf_score = performance.get("score", 0.7)
        if perf_score > 0.8:
            report_lines.append("⚡ PERFORMANCE: ✅ Efficient implementation")
        elif perf_score > 0.6:
            report_lines.append("⚡ PERFORMANCE: ✅ Good performance characteristics")
        else:
            report_lines.append("⚡ PERFORMANCE: ⚠️ Performance optimizations recommended")
        
        for rec in performance.get("recommendations", []):
            report_lines.append(f"   💡 {rec}")
        
        # Code statistics
        stats = result.details.get("statistics", {})
        if stats:
            report_lines.extend([
                "",
                "📊 CODE STATISTICS:",
                f"   Lines of code: {stats.get('code_lines', 0)}",
                f"   Comments: {stats.get('comment_lines', 0)}",
                f"   Variables: {stats.get('variable_count', 0)}",
                f"   Complexity score: {stats.get('complexity_score', 0):.1f}"
            ])
        
        # Final recommendation
        if result.success:
            report_lines.append("\n✅ Code is ready for deployment to PLC")
        else:
            report_lines.append("\n❌ Code requires fixes before deployment")
        
        return "\n".join(report_lines)
    
    async def quick_validate(self, code: str) -> bool:
        """Quick validation for simple pass/fail checks"""
        result = await self._run_comprehensive_validation(code)
        return result.success
