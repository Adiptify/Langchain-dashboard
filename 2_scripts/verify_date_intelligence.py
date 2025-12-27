import sys
import os

# Add core to path
sys.path.append(os.path.join(os.getcwd(), '1_core'))

from embedding_store import EmbeddingStore

def test_date_intelligence():
    store = EmbeddingStore()
    
    test_queries = [
        "What was the consumption in 12?",
        "Total energy for Dec",
        "Show me stats for December",
        "How much in 12/24?"
    ]
    
    print("="*60)
    print("DATE INTELLIGENCE VERIFICATION")
    print("="*60)
    
    for q in test_queries:
        print(f"\nQUERY: '{q}'")
        results = store.search(q, k=3)
        print(f"RESULTS FOUND: {len(results)}")
        for r in results:
            print(f"- [{r['match_type'].upper()}] {r['content'][:100]}...")
            if 'aliases' in r.get('metadata', {}):
                print(f"  Aliases: {r['metadata']['aliases']}")
    
    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_date_intelligence()
