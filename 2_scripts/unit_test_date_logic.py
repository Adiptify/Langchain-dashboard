import sys
import os
sys.path.append(os.path.join(os.getcwd(), '1_core'))

from smart_preprocessor import JSWEnergyPreprocessor
from embedding_store import EmbeddingStore

def test_logic():
    p = JSWEnergyPreprocessor()
    e = EmbeddingStore()
    
    print("--- Testing Alias Generation ---")
    dec_aliases = p.get_date_aliases("DEC", is_month=True)
    print(f"Aliases for 'DEC': {dec_aliases}")
    
    date_aliases = p.get_date_aliases("2024-12-25")
    print(f"Aliases for '2024-12-25': {date_aliases}")
    
    print("\n--- Testing Search Expansion ---")
    query_12 = e._extract_keywords("What was the consumption in 12?")
    print(f"Keywords for '12': {query_12}")
    
    query_dec = e._extract_keywords("How much for Dec 2024?")
    print(f"Keywords for 'Dec 2024': {query_dec}")
    
    # Assertions
    assert "12" in dec_aliases
    assert "DECEMBER" in dec_aliases
    assert "DEC" in query_12
    assert "12" in query_dec
    
    print("\n✅ LOGIC VERIFIED!")

if __name__ == "__main__":
    test_logic()
