import sys
import logging
from pathlib import Path

# Fix path to import from src
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from law.db.vector_store import VectorStore

logging.basicConfig(level=logging.WARNING)

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/rag_search.py 'query'")
        sys.exit(1)
        
    query = sys.argv[1]
    vs = VectorStore()
    
    print(f"\n🔎 Searching for: '{query}'")
    results = vs.search(query, n_results=3)
    
    print("\n" + "="*60)
    print(f"RAG Search Results")
    print("="*60)
    
    for i in range(len(results['ids'][0])):
        doc_id = results['ids'][0][i]
        content = results['documents'][0][i][:300].replace('\n', ' ') + "..."
        meta = results['metadatas'][0][i]
        score = 1.0 - results['distances'][0][i]
        
        print(f"\n[{i+1}] ID: {doc_id} | Similarity: {score:.4f}")
        print(f"    Source: {meta.get('source')} | Type: {meta.get('type')}")
        if meta.get('case_name'): print(f"    Title: {meta.get('case_name')}")
        if meta.get('law_name'): print(f"    Law: {meta.get('law_name')} ({meta.get('article')})")
        print(f"    Content: {content}")

if __name__ == "__main__":
    main()