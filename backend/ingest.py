# ingest.py
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from backend.tools.knowledge_base import initialize_knowledge_base, get_knowledge_stats

def main():
    """
    Enhanced knowledge base initialization script
    
    This script:
    1. Initializes ChromaDB and embedding model
    2. Ingests built-in IEC 61131-3 knowledge
    3. Processes any PDF files in knowledge_base/documents/
    4. Provides detailed status and statistics
    """
    
    print("🚀 AutoPLC Knowledge Base Initialization")
    print("=" * 50)
    
    try:
        # Initialize the knowledge base
        initialize_knowledge_base()
        
        # Get and display statistics
        stats = get_knowledge_stats()
        
        print("\n📊 Knowledge Base Statistics:")
        print(f"   Total chunks: {stats.get('total_chunks', 0)}")
        print(f"   Status: {stats.get('status', 'unknown')}")
        
        if 'sources' in stats:
            print("\n📚 Sources breakdown:")
            for source, count in stats['sources'].items():
                print(f"   • {source}: {count} chunks")
        
        print("\n✅ Knowledge Base Initialization Complete!")
        print("\n💡 Next Steps:")
        print("   1. Add your NVIDIA API keys to .env file")
        print("   2. Run: python backend/app.py")
        print("   3. Open: http://localhost:5001")
        
    except Exception as e:
        print(f"\n❌ Initialization failed: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("   • Check that ChromaDB can write to the project directory")
        print("   • Ensure sentence-transformers is properly installed")
        print("   • Verify Python path and imports")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
