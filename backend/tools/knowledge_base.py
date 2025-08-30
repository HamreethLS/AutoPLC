import chromadb
import os

# --- GLOBAL CLIENT AND COLLECTION ---
# This makes the connection persistent across function calls
client = None
collection = None
DB_PATH = "plc_knowledge_base"

def initialize_knowledge_base():
    """Initializes the ChromaDB client and collection."""
    global client, collection
    if client is None:
        # Check if the database directory exists
        if not os.path.exists(DB_PATH):
            print(f"Knowledge base not found at '{DB_PATH}'. Please run ingest.py first.")
            # Create the directory to avoid errors on the first run
            os.makedirs(DB_PATH)
            
        client = chromadb.PersistentClient(path=DB_PATH)
        
        try:
            # Try to get the collection, if it doesn't exist, it will raise an exception
            collection = client.get_collection(name="iec_61131_3_standard")
            print("Knowledge base loaded successfully.")
        except Exception as e:
            # If the collection doesn't exist, create it
            print("Knowledge base collection not found. Creating a new one.")
            collection = client.create_collection(name="iec_61131_3_standard")

def add_to_knowledge_base(documents: list, ids: list):
    """Adds documents to the ChromaDB collection."""
    initialize_knowledge_base()
    if not documents:
        print("No documents to add.")
        return
    collection.add(documents=documents, ids=ids)
    print(f"Added {len(documents)} documents to the knowledge base.")

def query_knowledge_base(query_text: str) -> str:
    """
    Queries the knowledge base for relevant information.
    This function is registered as a tool for an AutoGen agent.
    """
    initialize_knowledge_base()
    if collection is None or collection.count() == 0:
        return "Knowledge base is empty or not initialized. Please run the ingestion script."
        
    results = collection.query(
        query_texts=[query_text],
        n_results=3  # Return the top 3 most relevant chunks
    )
    
    if not results or not results['documents'][0]:
        return f"No relevant information found for: '{query_text}'"
        
    # Join the results into a single string
    context = "\n".join(results['documents'][0])
    return f"Context from knowledge base for '{query_text}':\n---\n{context}\n---"

