"""
Enhanced Compiler Integration with robust error handling and detailed reporting
"""

import os
import subprocess
import tempfile
import re
import asyncio
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class CompilerResult:
    def __init__(self, success: bool, output: str, errors: List[str], warnings: List[str]):
        self.success = success
        self.output = output
        self.errors = errors
        self.warnings = warnings
        self.error_count = len(errors)
        self.warning_count = len(warnings)

class EnhancedCompiler:
    """Enhanced compiler with better error handling and reporting"""
    
    def __init__(self):
        self.matiec_path = self._find_matiec_path()
        self.temp_dir = Path(tempfile.gettempdir()) / "autoplc_compile"
        self.temp_dir.mkdir(exist_ok=True)
        
    def _find_matiec_path(self) -> Optional[str]:
        """Find MATIEC installation path"""
        
        # Try environment variable first
        env_path = os.getenv("MATIEC_PATH")
        if env_path and os.path.exists(env_path):
            return env_path
        
        # Try common installation paths
        common_paths = [
            "/usr/local/bin/matiec",
            "/usr/bin/matiec", 
            "/opt/matiec/bin",
            "C:\\matiec\\bin",
            "C:\\OpenPLC_Editor\\matiec",
            "C:\\Program Files\\matiec"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def compile_code(self, code: str) -> CompilerResult:
        """Compile Structured Text code with enhanced error handling"""
        
        if not self.matiec_path:
            return CompilerResult(
                success=False,
                output="",
                errors=["MATIEC compiler not found. Please install MATIEC and set MATIEC_PATH environment variable."],
                warnings=[]
            )
        
        # Create a temporary file for the code
        st_file_path = ""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.st', dir=self.temp_dir, delete=False, encoding='utf-8'
        ) as st_file:
            st_file.write(code)
            st_file_path = st_file.name

        try:
            # Command to run the compiler
            output_dir = self.temp_dir
            command = [self.matiec_path, "-I", str(output_dir), str(st_file_path)]

            # Execute the compiler
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,  # 30-second timeout
                check=False  # Don't raise exception on non-zero exit code
            )

            output = process.stdout + "\n" + process.stderr
            errors = []
            warnings = []

            # Parse output for errors and warnings
            for line in output.splitlines():
                if "error:" in line.lower():
                    errors.append(line)
                elif "warning:" in line.lower():
                    warnings.append(line)

            success = process.returncode == 0 and not errors

            return CompilerResult(success=success, output=output, errors=errors, warnings=warnings)

        except subprocess.TimeoutExpired:
            return CompilerResult(
                success=False,
                output="Compiler process timed out.",
                errors=["Compilation took too long and was terminated."],
                warnings=[]
            )
        except Exception as e:
            return CompilerResult(success=False, output=str(e), errors=[f"An unexpected error occurred during compilation: {e}"], warnings=[])
        finally:
            if os.path.exists(st_file_path):
                os.remove(st_file_path)

# Global enhanced compiler instance
enhanced_compiler = EnhancedCompiler()

def run_iec2c_compiler(code: str) -> str:
    """Legacy function for backward compatibility"""
    result = enhanced_compiler.compile_code(code)
    
    if result.success:
        return "✅ Compilation Successful."
    else:
        error_summary = "\n".join(result.errors[:5])
        return f"❌ Compilation Failed:\n{error_summary}"
