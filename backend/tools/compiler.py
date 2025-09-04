# backend/tools/compiler.py
import os
import subprocess
import tempfile
import re
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

def run_iec2c_compiler(code: str) -> str:
    """
    Enhanced compiler integration with better error handling and reporting
    
    Args:
        code: A string containing the full Structured Text program
        
    Returns:
        A string containing "Compilation Successful." or detailed error information
    """
    
    # Get MATIEC path from environment or use existing path
    matiec_path = os.getenv("MATIEC_PATH", r"C:\Users\L.S. HAMREETH\OpenPLC_Editor\matiec")
    
    if not os.path.exists(matiec_path):
        return f"Error: MATIEC installation not found at: {matiec_path}\nPlease update MATIEC_PATH in your .env file"
    
    # Use temporary file with better naming
    temp_file_path = f"autoplc_temp_{os.getpid()}.st"
    full_temp_path = os.path.join(matiec_path, temp_file_path)
    
    try:
        # Write code to temporary file with UTF-8 encoding
        with open(full_temp_path, "w", encoding="utf-8") as f:
            f.write(code)
        
        # Run compiler
        command = ["iec2c", temp_file_path]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=matiec_path,
            timeout=30  # Add timeout for safety
        )
        
        if result.returncode == 0:
            return "✅ Compilation Successful."
        else:
            # Enhanced error reporting
            error_output = result.stderr.strip()
            if not error_output:
                error_output = result.stdout.strip()
            
            # Clean up error messages for better readability
            cleaned_errors = clean_compiler_errors(error_output)
            return f"❌ Compilation Failed:\n{cleaned_errors}"
            
    except subprocess.TimeoutExpired:
        return "❌ Compilation Failed: Compiler timeout (code may have infinite loops)"
    except FileNotFoundError:
        return "❌ Error: 'iec2c' command not found. Please ensure MATIEC is properly installed."
    except Exception as e:
        return f"❌ Compilation Error: {str(e)}"
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(full_temp_path):
                os.remove(full_temp_path)
        except:
            pass  # Ignore cleanup errors

def clean_compiler_errors(error_text: str) -> str:
    """Clean and format compiler error messages for better readability."""
    
    if not error_text:
        return "Unknown compilation error"
    
    # Common error patterns and their clean versions
    error_patterns = [
        (r"ERROR at line (\d+)", r"Line \1 Error"),
        (r"syntax error, unexpected (.+)", r"Syntax Error: Unexpected \1"),
        (r"undeclared variable '(.+)'", r"Undeclared Variable: '\1'"),
        (r"type mismatch", "Type Mismatch Error"),
    ]
    
    cleaned = error_text
    for pattern, replacement in error_patterns:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    
    # Remove file paths and keep only relevant error info
    lines = cleaned.split('\n')
    relevant_lines = []
    
    for line in lines:
        line = line.strip()
        if line and not line.startswith('/') and not line.startswith('C:'):
            relevant_lines.append(line)
    
    return '\n'.join(relevant_lines[:10])  # Limit to first 10 error lines

def validate_st_syntax_patterns(code: str) -> Dict:
    """
    Pre-compilation syntax validation using regex patterns
    
    Args:
        code: ST code to validate
        
    Returns:
        Dict with validation results
    """
    
    issues = []
    warnings = []
    
    # Check basic structure
    if not re.search(r"PROGRAM\s+\w+", code, re.IGNORECASE):
        issues.append("Missing PROGRAM declaration")
    
    if not re.search(r"END_PROGRAM", code, re.IGNORECASE):
        issues.append("Missing END_PROGRAM")
    
    # Check for VAR block
    var_match = re.search(r"VAR(.*?)END_VAR", code, re.DOTALL | re.IGNORECASE)
    if not var_match:
        warnings.append("No VAR...END_VAR block found")
    
    # Check for BEGIN section
    if not re.search(r"BEGIN", code, re.IGNORECASE):
        issues.append("Missing BEGIN keyword")
    
    # Check comment syntax
    if "//" in code:
        issues.append("Invalid comment syntax: '//' not allowed, use '(* *)'")
    
    if "/*" in code or "*/" in code:
        issues.append("Invalid comment syntax: '/* */' not allowed, use '(* *)'")
    
    # Check for forbidden function blocks
    forbidden_blocks = ["TON", "TOF", "CTU", "CTD", "RTRIG", "FTRIG", "TP", "TONR"]
    for block in forbidden_blocks:
        if re.search(rf"\b{block}\b", code, re.IGNORECASE):
            issues.append(f"Forbidden function block: {block} (use manual implementation)")
    
    # Check for loops in main logic (dangerous for scan cycle)
    dangerous_loops = ["WHILE", "FOR", "REPEAT"]
    for loop in dangerous_loops:
        if re.search(rf"\b{loop}\b", code, re.IGNORECASE):
            warnings.append(f"Warning: {loop} loop detected (may cause scan cycle issues)")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "issue_count": len(issues),
        "warning_count": len(warnings)
    }

def get_compiler_info() -> Dict:
    """Get information about the compiler installation."""
    
    matiec_path = os.getenv("MATIEC_PATH", r"C:\Users\L.S. HAMREETH\OpenPLC_Editor\matiec")
    
    info = {
        "matiec_path": matiec_path,
        "path_exists": os.path.exists(matiec_path),
        "compiler_available": False,
        "version": "unknown"
    }
    
    if info["path_exists"]:
        try:
            # Test compiler availability
            result = subprocess.run(
                ["iec2c", "--help"],
                capture_output=True,
                text=True,
                cwd=matiec_path,
                timeout=10
            )
            
            info["compiler_available"] = result.returncode == 0
            
            if info["compiler_available"]:
                # Try to extract version info
                version_result = subprocess.run(
                    ["iec2c", "--version"],
                    capture_output=True,
                    text=True,
                    cwd=matiec_path,
                    timeout=5
                )
                if version_result.returncode == 0:
                    info["version"] = version_result.stdout.strip()
                    
        except Exception as e:
            info["error"] = str(e)
    
    return info
