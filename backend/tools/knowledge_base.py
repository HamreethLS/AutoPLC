# backend/tools/knowledge_base.py
import os
import chromadb
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from typing import List, Dict, Optional
import json

# --- GLOBAL VARIABLES ---
client = None
collection = None
embedding_model = None

# --- ENHANCED: Define paths ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)  # backend/
ROOT_DIR = os.path.dirname(PARENT_DIR)   # project root
DB_PATH = os.path.join(ROOT_DIR, "knowledge_base", "chroma_db")
DOCUMENTS_PATH = os.path.join(ROOT_DIR, "knowledge_base", "documents")

def initialize_knowledge_base():
    """Initializes the ChromaDB client and collection, and loads the embedding model."""
    global client, collection, embedding_model
    
    if collection is not None:
        return
    
    print("🧠 Initializing Knowledge Base...")
    
    try:
        # Ensure directories exist
        os.makedirs(DB_PATH, exist_ok=True)
        os.makedirs(DOCUMENTS_PATH, exist_ok=True)
        
        print(f"📂 Using ChromaDB path: {DB_PATH}")
        print(f"📁 Documents path: {DOCUMENTS_PATH}")
        
        client = chromadb.PersistentClient(path=DB_PATH)
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        collection_name = "plc_knowledge_base"
        collection = client.get_or_create_collection(name=collection_name)
        
        # Enhanced ingestion check
        if collection.count() == 0:
            print("📚 Knowledge base is empty. Running enhanced ingestion...")
            ingest_documents_and_builtin_knowledge()
        else:
            print(f"✅ Knowledge base loaded. Collection count: {collection.count()}")
            
    except Exception as e:
        print(f"❌ FATAL Error initializing knowledge base: {e}")
        raise

def ingest_documents_and_builtin_knowledge():
    """Enhanced ingestion: Combines PDF documents with built-in IEC knowledge."""
    global collection, embedding_model
    
    if collection is None or embedding_model is None:
        print("❌ Error: Knowledge base not initialized. Cannot ingest documents.")
        return
    
    all_chunks = []
    metadata_list = []
    
    try:
        # PART 1: Built-in IEC 61131-3 Documentation
        builtin_knowledge = get_builtin_iec_knowledge()
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800, 
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", ".", ""]
        )
        
        for doc_name, content in builtin_knowledge.items():
            chunks = text_splitter.split_text(content)
            for i, chunk in enumerate(chunks):
                if chunk.strip():
                    all_chunks.append(chunk.strip())
                    metadata_list.append({
                        "source": doc_name,
                        "type": "builtin",
                        "chunk_id": len(all_chunks) - 1
                    })
        
        print(f"📖 Added {len([c for c in all_chunks if any(m['source'] == src for m in metadata_list for src in builtin_knowledge.keys())])} chunks from built-in knowledge")
        
        # PART 2: PDF Documents (if any exist)
        pdf_count = 0
        if os.path.exists(DOCUMENTS_PATH):
            for filename in os.listdir(DOCUMENTS_PATH):
                if filename.lower().endswith(".pdf"):
                    pdf_count += 1
                    filepath = os.path.join(DOCUMENTS_PATH, filename)
                    print(f"📄 Processing PDF: {filename}...")
                    
                    # Extract text from PDF
                    doc = fitz.open(filepath)
                    full_text = ""
                    for page_num, page in enumerate(doc):
                        page_text = page.get_text()
                        full_text += f"\n[Page {page_num + 1}]\n{page_text}"
                    doc.close()
                    
                    # Split the extracted text into chunks
                    chunks = text_splitter.split_text(full_text)
                    
                    for i, chunk in enumerate(chunks):
                        if chunk.strip():
                            all_chunks.append(chunk.strip())
                            metadata_list.append({
                                "source": filename,
                                "type": "pdf",
                                "chunk_id": len(all_chunks) - 1
                            })
                    
                    print(f"📊 Created {len(chunks)} chunks from {filename}")
        
        if pdf_count == 0:
            print("📁 No PDF files found in documents folder")
        
        # PART 3: Store in ChromaDB
        if not all_chunks:
            print("⚠️  No content to ingest.")
            return
        
        # Generate embeddings
        print("🔄 Generating embeddings...")
        embeddings = embedding_model.encode(all_chunks).tolist()
        
        # Create unique IDs
        ids = [f"chunk_{i}" for i in range(len(all_chunks))]
        
        # Add to collection with metadata
        collection.add(
            embeddings=embeddings,
            documents=all_chunks,
            ids=ids,
            metadatas=metadata_list
        )
        
        print(f"✅ Successfully ingested {len(all_chunks)} total chunks into knowledge base")
        print(f"📊 Built-in knowledge: {len([m for m in metadata_list if m['type'] == 'builtin'])} chunks")
        print(f"📊 PDF documents: {len([m for m in metadata_list if m['type'] == 'pdf'])} chunks")
        
    except Exception as e:
        print(f"❌ Error during document ingestion: {e}")
        raise

def get_builtin_iec_knowledge() -> Dict[str, str]:
    """Returns built-in IEC 61131-3 knowledge for immediate use."""
    
    return {
        "IEC_61131_3_Core_Principles": """
        IEC 61131-3 Structured Text (ST) Core Principles:
        
        1. Program Structure: A program must start with PROGRAM and end with END_PROGRAM. 
           All executable logic must be placed between the BEGIN and END_PROGRAM keywords. 
           The section between VAR and BEGIN is strictly for variable declarations.
        
        2. PLC Scan Cycle: The entire BEGIN...END_PROGRAM block is executed from top to bottom 
           repeatedly in a fast, continuous loop called the scan cycle. Therefore, you must not 
           use WHILE, REPEAT, or FOR loops for the main program flow, as this will cause an 
           infinite loop within a single scan cycle and halt the PLC.
        
        3. Comment Syntax: The only valid syntax for comments is (* This is a comment *). 
           The // and /* ... */ styles are not supported and will cause compilation errors.
        
        4. Variable Declaration: All variables must be declared in a VAR...END_VAR block before 
           the BEGIN keyword. Example: MyVariable : INT := 0;
        """,
        
        "IEC_61131_3_Data_Types": """
        Standard IEC 61131-3 Data Types:
        
        Elementary Data Types:
        - BOOL: Boolean (TRUE/FALSE)
        - SINT: Short integer (-128 to 127)
        - INT: Integer (-32768 to 32767) 
        - DINT: Double integer (-2147483648 to 2147483647)
        - REAL: Real numbers (floating point)
        - TIME: Duration (T#1s, T#100ms, etc.)
        - STRING: Text strings
        
        Bit Strings:
        - BYTE: 8 bits
        - WORD: 16 bits  
        - DWORD: 32 bits
        
        Variable Declaration Examples:
        - MyBoolean : BOOL := FALSE;
        - Temperature : REAL := 20.5;
        - Counter : INT := 0;
        - DelayTime : TIME := T#5s;
        """,
        
        "IEC_61131_3_Operators": """
        IEC 61131-3 Operators and Expressions:
        
        Comparison Operators:
        - = (equal to)
        - <> (not equal to)
        - < (less than)
        - <= (less than or equal to)
        - > (greater than)
        - >= (greater than or equal to)
        
        Logical Operators:
        - AND (logical and)
        - OR (logical or)  
        - XOR (exclusive or)
        - NOT (logical not)
        
        Arithmetic Operators:
        - + (addition)
        - - (subtraction)
        - * (multiplication)
        - / (division)
        - MOD (modulo)
        
        Assignment:
        - := (assignment operator)
        """,
        
        "Timer_Implementation_Guidelines": """
        Timer Implementation Without TON Function Blocks:
        
        Since standard function blocks like TON are not always available, implement timers using:
        
        1. TIME variables to store start times
        2. Manual elapsed time calculation
        3. Boolean flags for timer state
        
        Example Timer Pattern:
        VAR
            TimerStartTime : TIME;
            TimerActive : BOOL := FALSE;
            TimerDone : BOOL := FALSE;
            DelayPeriod : TIME := T#5s;
        END_VAR
        
        BEGIN
            IF StartCondition AND NOT TimerActive THEN
                TimerStartTime := CURRENT_TIME;
                TimerActive := TRUE;
                TimerDone := FALSE;
            END_IF;
            
            IF TimerActive AND ((CURRENT_TIME - TimerStartTime) >= DelayPeriod) THEN
                TimerDone := TRUE;
                TimerActive := FALSE;
            END_IF;
        END_PROGRAM
        """,
        
        "Safety_and_Best_Practices": """
        Safety and Best Practices for PLC Programming:
        
        1. Emergency Stop Priority: Always check emergency stop conditions first
        2. Fail-Safe Design: Default to safe states when conditions are uncertain
        3. Input Validation: Validate sensor inputs before using them
        4. Interlocking: Prevent unsafe operational combinations
        5. Clear Variable Names: Use descriptive names (StartButton vs Inp1)
        6. Consistent Naming: Choose either snake_case or PascalCase and stick to it
        7. Magic Numbers: Use named constants instead of hardcoded values
        8. Modular Logic: Break complex logic into clear conditional blocks
        9. Comments: Document complex logic and safety considerations
        10. Testing Values: Use static TRUE/FALSE values for initial testing
        """,
        
        "Common_Control_Patterns": """
        Common PLC Control Patterns:
        
        1. Start/Stop with Latching:
        IF StartButton AND NOT StopButton THEN
            MotorRunning := TRUE;
        ELSIF StopButton THEN
            MotorRunning := FALSE;
        END_IF;
        
        2. Sequential Control:
        CASE CurrentStep OF
        0: (* Initialize *)
           IF InitComplete THEN CurrentStep := 1; END_IF;
        1: (* Step 1 *)
           IF Step1Complete THEN CurrentStep := 2; END_IF;
        2: (* Step 2 *)
           IF Step2Complete THEN CurrentStep := 0; END_IF;
        END_CASE;
        
        3. Counter Implementation:
        IF CountEnable AND CountInput THEN
            Counter := Counter + 1;
            CountInput := FALSE; (* Edge detection *)
        END_IF;
        
        4. Alarm Logic:
        IF ProcessValue > HighLimit THEN
            HighAlarm := TRUE;
        ELSIF ProcessValue < (HighLimit - Hysteresis) THEN
            HighAlarm := FALSE;
        END_IF;
        """
    }

def query_knowledge_base(query: str, max_results: int = 3) -> str:
    """Enhanced knowledge base query with better result processing."""
    global collection, embedding_model
    
    if collection is None or embedding_model is None:
        return "Error: Knowledge base is not initialized."
    
    if collection.count() == 0:
        return "Knowledge base is empty. Please ensure the ingestion process has run successfully."
    
    try:
        # Generate query embedding
        query_embedding = embedding_model.encode([query]).tolist()
        
        # Enhanced query with metadata filtering
        results = collection.query(
            query_embeddings=query_embedding, 
            n_results=max_results,
            include=['documents', 'metadatas', 'distances']
        )
        
        # Process results with metadata
        docs = results.get('documents', [[]])
        metadatas = results.get('metadatas', [[]])
        distances = results.get('distances', [[]])
        
        if not docs or not docs[0]:
            return "No relevant information found for that query."
        
        # Format results with source attribution
        formatted_results = []
        for i, doc in enumerate(docs[0]):
            if doc and doc.strip():
                metadata = metadatas[0][i] if metadatas and metadatas[0] else {}
                source = metadata.get('source', 'unknown')
                doc_type = metadata.get('type', 'unknown')
                
                formatted_doc = f"[Source: {source} ({doc_type})]\n{doc.strip()}"
                formatted_results.append(formatted_doc)
        
        if not formatted_results:
            return "No relevant information found for that query."
        
        context = "\n\n" + "="*50 + "\n\n".join(formatted_results)
        
        return f"Found relevant context from the knowledge base:\n{context}"
        
    except Exception as e:
        return f"An error occurred while querying the knowledge base: {e}"

def add_to_knowledge_base(documents: List[str], ids: List[str], metadatas: List[Dict] = None) -> bool:
    """Add new documents to the knowledge base."""
    global collection, embedding_model
    
    try:
        if collection is None or embedding_model is None:
            print("❌ Knowledge base not initialized")
            return False
        
        embeddings = embedding_model.encode(documents).tolist()
        
        if metadatas:
            collection.add(
                embeddings=embeddings,
                documents=documents,
                ids=ids,
                metadatas=metadatas
            )
        else:
            collection.add(
                embeddings=embeddings,
                documents=documents,
                ids=ids
            )
        
        print(f"✅ Added {len(documents)} new documents to knowledge base")
        return True
        
    except Exception as e:
        print(f"❌ Error adding to knowledge base: {e}")
        return False

def get_knowledge_stats() -> Dict:
    """Get statistics about the knowledge base."""
    global collection
    
    if collection is None:
        return {"error": "Knowledge base not initialized"}
    
    try:
        count = collection.count()
        
        # Get sample of metadatas to analyze sources
        sample_size = min(100, count)
        if count > 0:
            sample = collection.get(limit=sample_size, include=['metadatas'])
            metadatas = sample.get('metadatas', [])
            
            sources = {}
            for metadata in metadatas:
                source = metadata.get('source', 'unknown')
                doc_type = metadata.get('type', 'unknown')
                key = f"{source} ({doc_type})"
                sources[key] = sources.get(key, 0) + 1
        else:
            sources = {}
        
        return {
            "total_chunks": count,
            "sources": sources,
            "status": "healthy" if count > 0 else "empty"
        }
        
    except Exception as e:
        return {"error": f"Failed to get stats: {e}"}

def search_knowledge_base(query: str, source_filter: Optional[str] = None) -> List[Dict]:
    """Advanced search with filtering and ranking."""
    global collection, embedding_model
    
    if collection is None or embedding_model is None:
        return []
    
    try:
        query_embedding = embedding_model.encode([query]).tolist()
        
        # Advanced query with filtering
        where_filter = {}
        if source_filter:
            where_filter = {"source": {"$eq": source_filter}}
        
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=5,
            include=['documents', 'metadatas', 'distances'],
            where=where_filter if where_filter else None
        )
        
        # Format as structured results
        formatted_results = []
        docs = results.get('documents', [[]])
        metadatas = results.get('metadatas', [[]])
        distances = results.get('distances', [[]])
        
        for i, doc in enumerate(docs[0] if docs else []):
            if doc:
                metadata = metadatas[0][i] if metadatas and len(metadatas[0]) > i else {}
                distance = distances[0][i] if distances and len(distances[0]) > i else 1.0
                
                formatted_results.append({
                    "content": doc,
                    "source": metadata.get('source', 'unknown'),
                    "type": metadata.get('type', 'unknown'),
                    "relevance_score": 1 - distance,
                    "chunk_id": metadata.get('chunk_id', i)
                })
        
        return formatted_results
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        return []
