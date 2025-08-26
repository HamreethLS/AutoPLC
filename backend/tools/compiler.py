import os
import subprocess

def run_iec2c_compiler(code: str) -> str:
    """
    Saves the given Structured Text code to a temporary file and compiles
    it using the iec2c compiler to check for syntax errors.

    Args:
        code: A string containing the full Structured Text program.

    Returns:
        A string containing "Compilation Successful." or the compiler's error message.
    """
    # --- ACTION REQUIRED ---
    # 1. Find your matiec installation directory.
    # 2. Replace the placeholder below with the absolute path to that directory.
    #    Example for Windows: r"C:\Program Files\matiec"
    #    Example for Linux: "/usr/local/share/matiec"
    matiec_path = r"C:\Users\L.S. HAMREETH\OpenPLC_Editor\matiec"

    if "YOUR_MATIEC_INSTALLATION_PATH_HERE" in matiec_path:
        return "Error: Please update the 'matiec_path' variable in backend/tools/compiler.py"

    temp_file_path = "temp_program.st"
    # To avoid path issues, create the temp file in the matiec directory
    full_temp_path = os.path.join(matiec_path, temp_file_path)

    with open(full_temp_path, "w") as f:
        f.write(code)

    try:
        command = ["iec2c", temp_file_path]
        
        # We now run the command from within the matiec installation directory.
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            cwd=matiec_path # This tells the compiler where to run from.
        )
        
        return "Compilation Successful."
        
    except FileNotFoundError:
        return "Error: 'iec2c' command not found. Please ensure it is installed and in your PATH."
        
    except subprocess.CalledProcessError as e:
        return f"Compilation Failed:\n{e.stderr}"
        
    finally:
        # Clean up the temporary file
        if os.path.exists(full_temp_path):
            os.remove(full_temp_path)
