import os
from backend.tools.knowledge_base import add_to_knowledge_base, DB_PATH

# --- DOCUMENTATION CONTENT ---
# In a real-world scenario, this would be loaded from PDFs, websites, etc.
# For this example, we'll use a string with key facts about ST programming.
IEC_DOCUMENTATION = """
IEC 61131-3 Structured Text (ST) Core Principles:

1. Program Structure: A program must start with `PROGRAM <name>` and end with `END_PROGRAM`. All executable logic must be placed between the `BEGIN` and `END_PROGRAM` keywords. The section between `VAR` and `BEGIN` is strictly for variable declarations.

2. PLC Scan Cycle: The entire `BEGIN...END_PROGRAM` block is executed from top to bottom repeatedly in a fast, continuous loop called the scan cycle. Therefore, you must not use `WHILE`, `REPEAT`, or `FOR` loops for the main program flow, as this will cause an infinite loop within a single scan cycle and halt the PLC.

3. Comment Syntax: The only valid syntax for comments is `(* This is a comment *)`. The `//` and `/* ... */` styles are not supported and will cause compilation errors.

4. Variable Declaration: All variables must be declared in a `VAR...END_VAR` block before the `BEGIN` keyword. Example: `MyVariable : INT := 0;`.

5. Standard Function Blocks: The core standard does not include complex function blocks like `TON` (Timer On-Delay) or `CTU` (Counter Up) by default. Timers and counters must be implemented using basic logic with `TIME` variables and integer counters. For example, to create a delay, you must store a start time and continuously check the elapsed time against it.

6. Case Insensitivity: The ST language is case-insensitive. However, it is best practice to use consistent capitalization for readability (e.g., `MyVariable` is the same as `myvariable`).
"""

def ingest_data():
    """
    Chunks the documentation and adds it to the knowledge base.
    This should be run once before starting the main application.
    """
    print("Starting data ingestion...")
    
    # Simple chunking strategy (split by paragraphs)
    chunks = [chunk.strip() for chunk in IEC_DOCUMENTATION.split('\n\n') if chunk.strip()]
    ids = [f"doc_chunk_{i}" for i in range(len(chunks))]
    
    # Check if the database already exists to avoid re-ingesting
    if os.path.exists(DB_PATH) and os.listdir(DB_PATH):
        print("Knowledge base already exists. Skipping ingestion.")
        print("To re-ingest, please delete the 'plc_knowledge_base' directory.")
        return
        
    add_to_knowledge_base(documents=chunks, ids=ids)
    print("Data ingestion complete.")

if __name__ == "__main__":
    ingest_data()

