# ingest.py

import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from backend.tools.knowledge_base import initialize_knowledge_base, get_knowledge_stats

def main():
    """
    Knowledge base ingestion script.
    This script forces a re-ingestion of documents from the source directory.
    """
    print("🚀 AutoPLC Knowledge Base Ingestion")
    print("=" * 50)

    try:
        # Force re-ingestion of the knowledge base
        initialize_knowledge_base(force_reingest=True)

        # Get and display statistics
        stats = get_knowledge_stats()
        print("\n📊 Knowledge Base Statistics:")
        print(f" Total chunks: {stats.get('total_chunks', 0)}")
        print(f" Status: {stats.get('status', 'unknown')}")

        if 'sources' in stats and stats['sources']:
            print("\n📚 Sources breakdown:")
            for source, count in stats['sources'].items():
                print(f" • {source}: {count} chunks")

        print("\n✅ Knowledge Base Ingestion Complete!")
        print("\n💡 Next Steps:")
        print(" 1. Add your NVIDIA API keys to .env file")
        print(" 2. Run: python backend/app.py")
        print(" 3. Open: http://localhost:8000")

    except Exception as e:
        print(f"\n❌ Ingestion failed: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print(" • Ensure the 'knowledge_base/documents' directory exists and contains documents.")
        print(" • Check that langchain, chromadb, and sentence-transformers are installed.")
        return 1

    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
