# backend/tools/linter.py

import re
from typing import Dict, List, Tuple

def run_linter(code: str) -> str:
    """
    Enhanced static analysis for Structured Text code quality
    """
    warnings = []
    errors = []
    suggestions = []

    # Enhanced Analysis Rules

    # 1. Magic numbers detection (enhanced)
    magic_number_issues = check_magic_numbers(code)
    warnings.extend(magic_number_issues)

    # 2. Variable naming consistency (enhanced)
    naming_issues = check_variable_naming(code)
    warnings.extend(naming_issues)

    # 3. Nesting complexity (enhanced)
    nesting_issues = check_nesting_complexity(code)
    warnings.extend(nesting_issues)

    # 4. NEW: Comment quality analysis
    comment_issues = check_comment_quality(code)
    suggestions.extend(comment_issues)

    # 5. NEW: Safety pattern analysis
    safety_issues = check_safety_patterns(code)
    warnings.extend(safety_issues)

    # 6. NEW: Performance analysis
    performance_issues = check_performance_patterns(code)
    suggestions.extend(performance_issues)

    # 7. NEW: IEC compliance
    compliance_issues = check_iec_compliance(code)
    errors.extend(compliance_issues)

    # Format output
    if errors:
        return format_linter_output("ERRORS FOUND", errors, warnings, suggestions)
    elif warnings:
        return format_linter_output("WARNINGS FOUND", [], warnings, suggestions)
    elif suggestions:
        return format_linter_output("SUGGESTIONS", [], [], suggestions)
    else:
        return "✅ Linter Check Passed. Code follows best practices and quality standards."

def check_magic_numbers(code: str) -> List[str]:
    """Enhanced magic number detection."""
    issues = []

    # Pattern for numbers in conditionals
    conditional_pattern = r"(?:IF|ELSIF)\s+.*?([0-9]+)"
    conditional_numbers = re.findall(conditional_pattern, code, re.IGNORECASE)
    
    # Filter out common acceptable numbers (0, 1)
    magic_numbers = [num for num in conditional_numbers if int(num) > 1]
    unique_numbers = list(set(magic_numbers))
    
    if len(unique_numbers) > 1:
        issues.append(f"Magic Numbers: Found hardcoded values {unique_numbers} in conditionals. Consider using named constants.")

    # Pattern for timer values
    timer_pattern = r"T#(\d+)([smh])"
    timer_matches = re.findall(timer_pattern, code, re.IGNORECASE)
    if len(timer_matches) > 2:
        issues.append("Timer Values: Multiple hardcoded timer values found. Consider using TIME constants.")

    return issues

def check_variable_naming(code: str) -> List[str]:
    """Enhanced variable naming analysis."""
    issues = []

    # Extract all variable declarations
    var_blocks = re.findall(r"VAR(.*?)END_VAR", code, re.DOTALL | re.IGNORECASE)
    all_variables = []

    for block in var_blocks:
        # Match variable declarations: VarName : DataType
        var_declarations = re.findall(r"(\w+)\s*:\s*\w+", block)
        all_variables.extend(var_declarations)

    if not all_variables:
        return issues

    # Analyze naming patterns
    snake_case_vars = [v for v in all_variables if "_" in v]
    camel_case_vars = [v for v in all_variables if v[0].islower() and any(c.isupper() for c in v[1:])]
    pascal_case_vars = [v for v in all_variables if v[0].isupper() and any(c.isupper() for c in v[1:])]

    pattern_count = sum([
        1 if snake_case_vars else 0,
        1 if camel_case_vars else 0,
        1 if pascal_case_vars else 0
    ])

    if pattern_count > 1:
        issues.append(f"Inconsistent Naming: Mix of naming conventions detected. "
                     f"Snake_case: {len(snake_case_vars)}, camelCase: {len(camel_case_vars)}, "
                     f"PascalCase: {len(pascal_case_vars)}. Choose one style.")

    # Check for unclear variable names
    unclear_vars = [v for v in all_variables if len(v) < 3 or v.lower() in ['var', 'temp', 'x', 'y', 'z']]
    if unclear_vars:
        issues.append(f"Unclear Variables: Consider more descriptive names for: {unclear_vars}")

    return issues

def check_nesting_complexity(code: str) -> List[str]:
    """Enhanced nesting complexity analysis."""
    issues = []

    lines = code.split('\n')
    max_nesting = 0
    current_nesting = 0
    complex_blocks = []

    for line_num, line in enumerate(lines, 1):
        stripped_line = line.strip().upper()
        
        if any(stripped_line.startswith(kw) for kw in ['IF', 'CASE']):
            current_nesting += 1
            if current_nesting > max_nesting:
                max_nesting = current_nesting
            if current_nesting > 2:
                complex_blocks.append(f"Line {line_num}")
        elif any(stripped_line.startswith(kw) for kw in ['END_IF', 'END_CASE']):
            current_nesting = max(0, current_nesting - 1)

    if max_nesting > 3:
        issues.append(f"Deep Nesting: Found {max_nesting} levels of nesting at {complex_blocks}. "
                     f"Consider refactoring for better readability.")
    elif max_nesting > 2:
        issues.append(f"Moderate Nesting: {max_nesting} levels detected. Consider simplifying logic structure.")

    return issues

def check_comment_quality(code: str) -> List[str]:
    """Analyze comment quality and coverage."""
    suggestions = []

    # Count comments
    comment_matches = re.findall(r"\(\*.*?\*\)", code, re.DOTALL)
    code_lines = [line for line in code.split('\n') if line.strip() and not line.strip().startswith('(*')]

    if len(comment_matches) == 0:
        suggestions.append("No Comments: Consider adding comments to explain complex logic")
    elif len(comment_matches) / len(code_lines) < 0.1:
        suggestions.append("Few Comments: Consider adding more explanatory comments")

    # Check for TODO/FIXME comments
    todo_comments = [c for c in comment_matches if re.search(r"TODO|FIXME|HACK", c, re.IGNORECASE)]
    if todo_comments:
        suggestions.append(f"Pending Issues: Found {len(todo_comments)} TODO/FIXME comments")

    return suggestions

def check_safety_patterns(code: str) -> List[str]:
    """Analyze safety-related patterns in the code."""
    warnings = []

    # Check for emergency stop handling
    has_emergency_stop = bool(re.search(r"\bemergency\b", code, re.IGNORECASE))
    has_safety_logic = bool(re.search(r"\bsafe\b|\bfail.?safe\b", code, re.IGNORECASE))

    # Look for output controls without safety checks
    output_assignments = re.findall(r"(\w+)\s*:=\s*TRUE", code, re.IGNORECASE)

    if output_assignments and not (has_emergency_stop or has_safety_logic):
        warnings.append("Safety Check: No emergency stop or safety logic detected. "
                       "Consider adding safety interlocks for outputs.")

    # Check for input validation
    input_usage = re.findall(r"IF\s+(\w+)", code, re.IGNORECASE)
    if input_usage and len(set(input_usage)) > 3:
        warnings.append("Input Validation: Consider validating sensor inputs before using them in logic.")

    return warnings

def check_performance_patterns(code: str) -> List[str]:
    """Analyze performance-related patterns."""
    suggestions = []

    # Check for redundant calculations
    lines = code.split('\n')
    assignments = []

    for line in lines:
        if ':=' in line:
            assignments.append(line.strip())

    # Look for duplicate expressions
    expressions = [line.split(':=')[1].strip() for line in assignments if ':=' in line]
    duplicate_expressions = [expr for expr in set(expressions) if expressions.count(expr) > 1]

    if duplicate_expressions:
        suggestions.append(f"Performance: Duplicate expressions detected: {duplicate_expressions}. "
                          f"Consider using intermediate variables.")

    # Check for complex conditional expressions
    complex_conditions = re.findall(r"IF\s+(.+?)\s+THEN", code, re.IGNORECASE)
    for condition in complex_conditions:
        if condition.count('AND') + condition.count('OR') > 3:
            suggestions.append("Complex Conditions: Consider breaking down complex IF conditions "
                              "into intermediate boolean variables for clarity.")
            break

    return suggestions

def check_iec_compliance(code: str) -> List[str]:
    """Check for IEC 61131-3 compliance issues."""
    errors = []

    # Check program structure compliance
    structure_check = validate_program_structure(code)
    if not structure_check["valid"]:
        errors.extend(structure_check["errors"])

    # Check for invalid keywords or syntax
    invalid_keywords = ["goto", "label", "break", "continue"]
    for keyword in invalid_keywords:
        if re.search(rf"\b{keyword}\b", code, re.IGNORECASE):
            errors.append(f"IEC Compliance: '{keyword}' is not allowed in IEC 61131-3 ST")

    return errors

def validate_program_structure(code: str) -> Dict:
    """Validate overall program structure."""
    errors = []

    # Check for essential sections and their order
    program_match = re.search(r"PROGRAM\s+\w+", code, re.IGNORECASE)
    var_match = re.search(r"VAR.*END_VAR", code, re.DOTALL | re.IGNORECASE)
    end_program_match = re.search(r"END_PROGRAM", code, re.IGNORECASE)

    if not program_match:
        errors.append("Structure Error: Missing 'PROGRAM' declaration.")
    if not end_program_match:
        errors.append("Structure Error: Missing 'END_PROGRAM' statement.")
    
    # Check order if sections exist
    if program_match and var_match and program_match.start() > var_match.start():
        errors.append("Structure Error: 'VAR' block appears before 'PROGRAM' declaration.")
    
    if var_match and end_program_match and var_match.start() > end_program_match.start():
        errors.append("Structure Error: 'END_PROGRAM' appears before 'VAR' block.")

    if program_match and end_program_match and program_match.start() > end_program_match.start():
        errors.append("Structure Error: 'END_PROGRAM' appears before 'PROGRAM' declaration.")

    sections_found = []
    if program_match: sections_found.append("PROGRAM")
    if var_match: sections_found.append("VAR")
    if end_program_match: sections_found.append("END_PROGRAM")
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "sections_found": sections_found
    }

def format_linter_output(category: str, errors: List[str], warnings: List[str], suggestions: List[str]) -> str:
    """Format linter output in a readable way."""
    output_lines = []

    if category:
        output_lines.append(f"🔍 Linter Analysis - {category}")
        output_lines.append("=" * 50)

    if errors:
        output_lines.append("\n❌ ERRORS:")
        for i, error in enumerate(errors, 1):
            output_lines.append(f" {i}. {error}")

    if warnings:
        output_lines.append("\n⚠️ WARNINGS:")
        for i, warning in enumerate(warnings, 1):
            output_lines.append(f" {i}. {warning}")

    if suggestions:
        output_lines.append("\n💡 SUGGESTIONS:")
        for i, suggestion in enumerate(suggestions, 1):
            output_lines.append(f" {i}. {suggestion}")

    if not (errors or warnings or suggestions):
        output_lines.append("✅ All quality checks passed!")

    return "\n".join(output_lines)

def get_linter_stats(code: str) -> Dict:
    """Get comprehensive statistics about the code."""
    stats = {
        "total_lines": len(code.split('\n')),
        "code_lines": 0,
        "comment_lines": 0,
        "blank_lines": 0,
        "variable_count": 0,
        "complexity_score": 0
    }

    lines = code.split('\n')
    for line in lines:
        stripped = line.strip()
        if not stripped:
            stats["blank_lines"] += 1
        elif stripped.startswith('(*') or '(*' in stripped:
            stats["comment_lines"] += 1
        else:
            stats["code_lines"] += 1

    # Count variables
    var_blocks = re.findall(r"VAR(.*?)END_VAR", code, re.DOTALL | re.IGNORECASE)
    for block in var_blocks:
        variables = re.findall(r"(\w+)\s*:", block)
        stats["variable_count"] += len(variables)

    # Calculate complexity score
    complexity_factors = [
        len(re.findall(r"\bIF\b", code, re.IGNORECASE)) * 1,
        len(re.findall(r"\bCASE\b", code, re.IGNORECASE)) * 2,
        len(re.findall(r"\bAND\b|\bOR\b", code, re.IGNORECASE)) * 0.5,
    ]

    stats["complexity_score"] = sum(complexity_factors)

    return stats
