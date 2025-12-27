import sys
import os

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '1_core')))

from embedding_store import EmbeddingStore

def debug_rag():
    store = EmbeddingStore()
    queries = [
        "Show me the avg daily load for SECONDRY CRUSHER-3"
    ]
    
    print("="*60)
    print("RAG RETRIEVAL DEBUG RESULTS")
    print("="*60)
    
    for q in queries:
        print(f"\nQUERY: {q}")
        keywords = store._extract_keywords(q)
        print(f"KEYWORDS: {keywords}")
        
        results = store.search(q, k=5)
        print(f"RESULTS FOUND: {len(results)}")
        
        for i, r in enumerate(results, 1):
            m_type = r.get('match_type', 'unknown').upper()
            score = r.get('score', 0)
            content = r['content'][:150]
            print(f"  {i}. [{m_type}] Score: {score:.4f} | {content}...")

    print("="*60)

if __name__ == "__main__":
    debug_rag()
