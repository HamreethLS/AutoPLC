"""RAG system for PLC domain knowledge retrieval."""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import TextLoader, DirectoryLoader
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document


class PLCKnowledgeBase:
    """Knowledge base for PLC programming domain knowledge."""
    
    def __init__(self, knowledge_dir: str = "knowledge/data", persist_dir: str = "knowledge/vectorstore"):
        self.knowledge_dir = Path(knowledge_dir)
        self.persist_dir = Path(persist_dir)
        self.logger = logging.getLogger("knowledge_base")
        
        # Initialize embeddings model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize vector store
        self.vectorstore: Optional[Chroma] = None
        self._initialize_vectorstore()
    
    def _initialize_vectorstore(self):
        """Initialize or load the vector store."""
        try:
            # Create directories if they don't exist
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize Chroma vector store
            self.vectorstore = Chroma(
                persist_directory=str(self.persist_dir),
                embedding_function=self.embeddings,
                collection_name="plc_knowledge"
            )
            
            self.logger.info("Vector store initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize vector store: {str(e)}")
            raise
    
    def load_knowledge_documents(self):
        """Load PLC knowledge documents into the vector store."""
        if not self.knowledge_dir.exists():
            self.knowledge_dir.mkdir(parents=True, exist_ok=True)
            self._create_sample_knowledge()
        
        # Load documents from knowledge directory
        loader = DirectoryLoader(
            str(self.knowledge_dir),
            glob="**/*.txt",
            loader_cls=TextLoader,
            show_progress=True
        )
        
        try:
            documents = loader.load()
            self.logger.info(f"Loaded {len(documents)} documents")
            
            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            self.logger.info(f"Split into {len(chunks)} chunks")
            
            # Add to vector store
            if chunks:
                self.vectorstore.add_documents(chunks)
                self.vectorstore.persist()
                self.logger.info("Documents added to vector store and persisted")
            
        except Exception as e:
            self.logger.error(f"Failed to load knowledge documents: {str(e)}")
            raise
    
    def _create_sample_knowledge(self):
        """Create sample PLC knowledge documents."""
        sample_docs = {
            "iec61131_basics.txt": """
IEC 61131-3 Programming Languages

The IEC 61131-3 standard defines five programming languages for PLCs:

1. Structured Text (ST)
- High-level programming language similar to Pascal
- Supports complex mathematical operations
- Best for algorithms and data manipulation
- Example:
  IF temperature > 80 THEN
    cooling_valve := TRUE;
  ELSE
    cooling_valve := FALSE;
  END_IF;

2. Ladder Diagram (LD)
- Graphical language resembling electrical relay circuits
- Easy to understand for electricians
- Best for simple logic operations

3. Function Block Diagram (FBD)
- Graphical language using function blocks
- Shows data flow between functions
- Good for continuous control processes

4. Instruction List (IL)
- Low-level assembler-like language
- Compact and efficient
- Used for time-critical applications

5. Sequential Function Chart (SFC)
- High-level graphical language for sequential control
- Based on Petri nets
- Excellent for batch processes and state machines
""",
            
            "structured_text_syntax.txt": """
Structured Text (ST) Syntax Reference

Data Types:
- BOOL: Boolean values (TRUE, FALSE)
- INT: 16-bit signed integer (-32768 to 32767)
- DINT: 32-bit signed integer
- REAL: 32-bit floating point
- STRING: Character string
- TIME: Time duration (T#1s, T#100ms)
- ARRAY: Array of elements

Variable Declaration:
VAR
  temperature : REAL;
  pressure : INT;
  valve_open : BOOL := FALSE;
  timer1 : TON;
END_VAR

Control Structures:
- IF...THEN...ELSE...END_IF
- CASE...OF...END_CASE
- FOR...TO...DO...END_FOR
- WHILE...DO...END_WHILE
- REPEAT...UNTIL...END_REPEAT

Function Blocks:
- TON: Timer On Delay
- TOF: Timer Off Delay
- TP: Timer Pulse
- CTU: Counter Up
- CTD: Counter Down
- R_TRIG: Rising Edge Trigger
- F_TRIG: Falling Edge Trigger

Mathematical Operations:
- Arithmetic: +, -, *, /, MOD, **
- Comparison: =, <>, <, >, <=, >=
- Logical: AND, OR, XOR, NOT
""",
            
            "safety_guidelines.txt": """
PLC Safety Programming Guidelines

Safety Integrity Levels (SIL):
- SIL 1: Low risk, basic safety functions
- SIL 2: Medium risk, standard safety systems
- SIL 3: High risk, critical safety systems
- SIL 4: Very high risk, highest safety requirements

Safety Programming Principles:
1. Fail-Safe Design
   - System should fail to a safe state
   - Use normally closed contacts for safety inputs
   - Implement watchdog timers

2. Redundancy
   - Duplicate critical safety functions
   - Use diverse technologies where possible
   - Implement voting systems (2oo3, 1oo2)

3. Diagnostics
   - Continuous self-testing
   - Input/output monitoring
   - Communication diagnostics

4. Separation
   - Separate safety and non-safety functions
   - Use dedicated safety PLCs
   - Isolate safety networks

Common Safety Patterns:
- Emergency stop circuits
- Safety door monitoring
- Light curtain integration
- Two-hand control
- Speed monitoring
- Position monitoring

Testing Requirements:
- Proof testing intervals
- Functional safety testing
- Systematic capability verification
""",
            
            "common_patterns.txt": """
Common PLC Programming Patterns

1. Start/Stop Motor Control:
VAR
  start_button : BOOL;
  stop_button : BOOL;
  motor_run : BOOL;
  motor_feedback : BOOL;
END_VAR

motor_run := (start_button OR motor_run) AND NOT stop_button AND motor_feedback;

2. Timer-Based Sequence:
VAR
  step : INT := 0;
  timer : TON;
END_VAR

CASE step OF
  0: IF start_condition THEN
       step := 1;
       timer(IN:=TRUE, PT:=T#5s);
     END_IF;
  1: IF timer.Q THEN
       step := 2;
       timer(IN:=FALSE);
     END_IF;
END_CASE;

3. Analog Scaling:
FUNCTION ScaleAnalog : REAL
VAR_INPUT
  raw_value : INT;
  min_raw : INT := 0;
  max_raw : INT := 4095;
  min_scaled : REAL := 0.0;
  max_scaled : REAL := 100.0;
END_VAR

ScaleAnalog := min_scaled + (raw_value - min_raw) * (max_scaled - min_scaled) / (max_raw - min_raw);

4. PID Control:
VAR
  pid_controller : PID;
  setpoint : REAL;
  process_value : REAL;
  output : REAL;
END_VAR

pid_controller(
  AUTO := TRUE,
  SETPOINT := setpoint,
  PROCESS_VARIABLE := process_value,
  OUTPUT => output
);

5. State Machine:
TYPE
  States : (IDLE, RUNNING, STOPPING, ERROR);
END_TYPE

VAR
  current_state : States := IDLE;
END_VAR

CASE current_state OF
  IDLE: IF start_command THEN current_state := RUNNING; END_IF;
  RUNNING: IF stop_command THEN current_state := STOPPING; 
           ELSIF error_condition THEN current_state := ERROR; END_IF;
  STOPPING: IF stopped THEN current_state := IDLE; END_IF;
  ERROR: IF reset_command THEN current_state := IDLE; END_IF;
END_CASE;
"""
        }
        
        for filename, content in sample_docs.items():
            file_path = self.knowledge_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content.strip())
        
        self.logger.info(f"Created {len(sample_docs)} sample knowledge documents")
    
    def search_knowledge(self, query: str, k: int = 5) -> List[Document]:
        """Search for relevant knowledge based on query."""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized")
        
        try:
            results = self.vectorstore.similarity_search(query, k=k)
            self.logger.debug(f"Found {len(results)} relevant documents for query: {query}")
            return results
            
        except Exception as e:
            self.logger.error(f"Knowledge search failed: {str(e)}")
            return []
    
    def search_with_score(self, query: str, k: int = 5) -> List[tuple]:
        """Search for relevant knowledge with similarity scores."""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized")
        
        try:
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            self.logger.debug(f"Found {len(results)} scored results for query: {query}")
            return results
            
        except Exception as e:
            self.logger.error(f"Scored knowledge search failed: {str(e)}")
            return []
    
    def add_knowledge(self, content: str, metadata: Dict[str, Any] = None):
        """Add new knowledge to the vector store."""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized")
        
        # Create document
        doc = Document(page_content=content, metadata=metadata or {})
        
        # Split into chunks
        chunks = self.text_splitter.split_documents([doc])
        
        # Add to vector store
        self.vectorstore.add_documents(chunks)
        self.vectorstore.persist()
        
        self.logger.info(f"Added {len(chunks)} chunks to knowledge base")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        if not self.vectorstore:
            return {"status": "not_initialized"}
        
        try:
            collection = self.vectorstore._collection
            count = collection.count()
            
            return {
                "status": "initialized",
                "document_count": count,
                "embedding_model": "all-MiniLM-L6-v2",
                "persist_directory": str(self.persist_dir)
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}


class RAGRetriever:
    """Retrieval-Augmented Generation system for PLC knowledge."""
    
    def __init__(self, knowledge_base: PLCKnowledgeBase):
        self.knowledge_base = knowledge_base
        self.logger = logging.getLogger("rag_retriever")
    
    def retrieve_context(self, query: str, max_chunks: int = 5) -> str:
        """Retrieve relevant context for a query."""
        # Search for relevant documents
        results = self.knowledge_base.search_with_score(query, k=max_chunks)
        
        if not results:
            return "No relevant knowledge found."
        
        # Format context
        context_parts = []
        for doc, score in results:
            if score < 0.8:  # Only include high-relevance results
                context_parts.append(f"[Relevance: {1-score:.2f}]\n{doc.page_content}")
        
        if not context_parts:
            return "No highly relevant knowledge found."
        
        context = "\n\n---\n\n".join(context_parts)
        
        self.logger.debug(f"Retrieved context with {len(context_parts)} chunks")
        return context
    
    def retrieve_examples(self, task_type: str, language: str = "ST") -> List[str]:
        """Retrieve code examples for a specific task type."""
        query = f"{task_type} {language} example code pattern"
        results = self.knowledge_base.search_knowledge(query, k=3)
        
        examples = []
        for doc in results:
            # Extract code blocks from the content
            content = doc.page_content
            if "Example:" in content or "VAR" in content or "FUNCTION" in content:
                examples.append(content)
        
        return examples
    
    def retrieve_safety_guidelines(self, sil_level: int = None) -> str:
        """Retrieve safety guidelines for PLC programming."""
        query = "safety programming guidelines"
        if sil_level:
            query += f" SIL {sil_level}"
        
        results = self.knowledge_base.search_knowledge(query, k=3)
        
        guidelines = []
        for doc in results:
            if "safety" in doc.page_content.lower():
                guidelines.append(doc.page_content)
        
        return "\n\n".join(guidelines) if guidelines else "No safety guidelines found."
