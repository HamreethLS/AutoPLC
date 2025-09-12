# backend/tools/knowledge_base.py

import os
import shutil
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from typing import List, Dict, Optional

# --- GLOBAL VARIABLES ---
db = None
embeddings = None

# --- Define paths ---
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)  # backend/
ROOT_DIR = os.path.dirname(PARENT_DIR)  # project root

# Define knowledge base paths
KNOWLEDGE_BASE_DIR = os.path.join(ROOT_DIR, "knowledge_base")
SOURCE_DIRECTORY = os.path.join(KNOWLEDGE_BASE_DIR, "documents")
PERSIST_DIRECTORY = os.path.join(KNOWLEDGE_BASE_DIR, "chroma_db")
EMBEDDINGS_MODEL_NAME = os.environ.get('EMBEDDINGS_MODEL_NAME', 'all-MiniLM-L6-v2')


def initialize_knowledge_base(force_reingest: bool = False):
    """Initializes the ChromaDB client and collection, and loads the embedding model."""
    global db, embeddings

    if db is not None and not force_reingest:
        return

    print("🧠 Initializing Knowledge Base...")

    try:
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL_NAME)

        if force_reingest and os.path.exists(PERSIST_DIRECTORY):
            print(f"🗑️ Removing existing vector store for re-ingestion: {PERSIST_DIRECTORY}")
            shutil.rmtree(PERSIST_DIRECTORY)

        if not os.path.exists(PERSIST_DIRECTORY) or not os.listdir(PERSIST_DIRECTORY):
            print("📚 Knowledge base is empty or missing. Running ingestion...")
            ingest_documents()
        else:
            print(f"✅ Loading existing knowledge base from: {PERSIST_DIRECTORY}")

        # Load the persisted database
        db = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings)
        
        print(f"✅ Knowledge base loaded. Collection count: {db._collection.count()}")

    except Exception as e:
        print(f"❌ FATAL Error initializing knowledge base: {e}")
        raise

def ingest_documents():
    """Ingests markdown and source code documents from the source directory into the vector store."""
    global embeddings

    if embeddings is None:
        print("❌ Error: Embedding model not initialized. Cannot ingest documents.")
        return

    if not os.path.exists(SOURCE_DIRECTORY):
        print(f"⚠️ Source directory '{SOURCE_DIRECTORY}' not found. Creating it. Please add documents to it.")
        os.makedirs(SOURCE_DIRECTORY)
        return

    print(f"Ingesting documents from {SOURCE_DIRECTORY}")

    # --- 3. Load different file types ---
    print("Loading Markdown documents...")
    md_loader = DirectoryLoader(SOURCE_DIRECTORY, glob="**/*.md", loader_cls=TextLoader, show_progress=True, recursive=True)
    md_docs = md_loader.load()

    print("Loading source code documents...")
    code_extensions = ["**/*.py", "**/*.c", "**/*.h", "**/*.cc", "**/*.hh", "**/*.def"]
    code_docs = []
    for ext in code_extensions:
        loader = DirectoryLoader(SOURCE_DIRECTORY, glob=ext, loader_cls=TextLoader, show_progress=True, recursive=True)
        code_docs.extend(loader.load())

    if not md_docs and not code_docs:
        print("⚠️ No documents found to ingest.")
        return

    # --- 4. Process each document type with the correct splitter ---
    # Process Markdown files
    md_chunks = []
    if md_docs:
        headers_to_split_on = [("##", "Section")]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        for doc in md_docs:
            md_chunks.extend(markdown_splitter.split_text(doc.page_content))

    # Process code files
    code_chunks = []
    if code_docs:
        code_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        code_chunks = code_splitter.split_documents(code_docs)

    # Combine all chunks
    all_chunks = md_chunks + code_chunks

    print(f"Split {len(md_docs) + len(code_docs)} documents into {len(all_chunks)} chunks.")

    if not all_chunks:
        print("⚠️ No chunks created after splitting. Check document content.")
        return

    # Create and persist the vector store
    vector_store = Chroma.from_documents(all_chunks, embeddings, persist_directory=PERSIST_DIRECTORY)
    vector_store.persist()
    print(f"✅ Ingestion complete. Vector store persisted to {PERSIST_DIRECTORY}")

def query_knowledge_base(query: str, max_results: int = 3) -> str:
    """Queries the knowledge base and returns a formatted string of results."""
    global db

    if db is None:
        return "Error: Knowledge base is not initialized."

    if db._collection.count() == 0:
        return "Knowledge base is empty. Please run the ingestion script."

    try:
        # Use similarity search to get documents
        results = db.similarity_search(query, k=max_results)

        if not results:
            return "No relevant information found for that query."

        # Format results with source attribution
        formatted_results = []
        for doc in results:
            source = doc.metadata.get('source', 'unknown')
            # The new splitter adds metadata like {'Section': 'Header Text'}
            section = doc.metadata.get('Section', '')
            source_display = f"{os.path.basename(source)}"
            if section:
                source_display += f" > {section}"
            
            formatted_doc = f"[Source: {source_display}]\n{doc.page_content.strip()}"
            formatted_results.append(formatted_doc)

        if not formatted_results:
            return "No relevant information found for that query."

        context = "\n\n" + "="*50 + "\n\n".join(formatted_results)
        return f"Found relevant context from the knowledge base:\n{context}"

    except Exception as e:
        return f"An error occurred while querying the knowledge base: {e}"

def add_to_knowledge_base(documents: List[str], metadatas: List[Dict] = None) -> bool:
    """Add new documents to the knowledge base."""
    global db

    try:
        if db is None:
            print("❌ Knowledge base not initialized")
            return False
        
        from langchain.docstore.document import Document
        docs_to_add = [Document(page_content=d, metadata=m or {}) for d, m in zip(documents, metadatas or [{} for _ in documents])]

        db.add_documents(docs_to_add)
        db.persist()

        print(f"✅ Added {len(documents)} new documents to knowledge base")
        return True

    except Exception as e:
        print(f"❌ Error adding to knowledge base: {e}")
        return False

def get_knowledge_stats() -> Dict:
    """Get statistics about the knowledge base."""
    global db

    if db is None:
        # Try to load it to get stats without fully initializing
        if os.path.exists(PERSIST_DIRECTORY):
            try:
                temp_db = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL_NAME))
                count = temp_db._collection.count()
            except Exception:
                count = 0
        else:
            count = 0
    else:
        count = db._collection.count()

    if count == 0:
        return {
            "total_chunks": 0,
            "sources": {},
            "status": "empty"
        }

    source_display_name = os.path.relpath(SOURCE_DIRECTORY, ROOT_DIR)
    return {
        "total_chunks": count,
        "sources": {source_display_name: "Multiple files (Markdown, Code)"},
        "status": "healthy"
    }

def search_knowledge_base(query: str, source_filter: Optional[str] = None) -> List[Dict]:
    """Advanced search with filtering and ranking."""
    global db

    if db is None:
        return []

    try:
        # Langchain Chroma wrapper's filter is a bit different.
        # It takes a dictionary for metadata filtering.
        filter_dict = {}
        if source_filter:
            filter_dict = {"source": source_filter}

        results = db.similarity_search_with_relevance_scores(query, k=5, filter=filter_dict)

        # Format as structured results
        formatted_results = []
        for doc, score in results:
            metadata = doc.metadata
            source = metadata.get('source', 'unknown')
            section = metadata.get('Section', '')

            formatted_results.append({
                "content": doc.page_content,
                "source": source,
                "section": section,
                "relevance_score": score,
            })

        return formatted_results

    except Exception as e:
        print(f"❌ Search error: {e}")
        return []
