#!/usr/bin/env python3
"""Ingest preprocessed JSW data into the system"""

import sys
import os
import time

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../1_core')))

from smart_preprocessor import JSWEnergyPreprocessor
from embedding_store import EmbeddingStore

print("\nINGESTING PREPROCESSED JSW ENERGY DATA")
print("="*60)

# Paths
data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../4_data/data_prototype'))
excel_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../4_data/Energy Consumption Daily Report MHS Ele - Copy.xlsx'))

# Clean old data
print("\nClearing old database...")
if os.path.exists(f'{data_dir}/indexes/faiss.index'):
    os.remove(f'{data_dir}/indexes/faiss.index')
if os.path.exists(f'{data_dir}/indexes/id_map.json'):
    os.remove(f'{data_dir}/indexes/id_map.json')
if os.path.exists(f'{data_dir}/metadata.db'):
    os.remove(f'{data_dir}/metadata.db')

# Process and ingest
print("\nLoading and processing Excel file...")
start_time = time.time()
processor = JSWEnergyPreprocessor()
docs = processor.process_file(excel_path)
process_time = time.time() - start_time

if not docs:
    print("❌ No documents were extracted. check the Excel file and preprocessor logic.")
    sys.exit(1)

print(f"\n💾 Adding {len(docs)} documents to embedding store...")
embed_start = time.time()
es = EmbeddingStore()
es.add_documents(docs)
embed_time = time.time() - embed_start

if es.faiss_index:
    print(f"\nCOMPLETE! Documents in store: {es.faiss_index.ntotal}")
    print(f"⏱️  Processing time: {process_time:.2f}s")
    print(f"⏱️  Embedding time: {embed_time:.2f}s")
    
    print("\n📝 Sample documents:")
    for i, doc in enumerate(docs[:3], 1):
        print(f"\n{i}. {doc.doc_type}:")
        print(f"   {doc.content[:120]}...")

    print(f"\n🔍 Testing search...")
    results = es.search("total plant consumption", k=3)
    if results:
        print(f"\nTop result found: {results[0]['content'][:150]}...")
    else:
        print(f"\n⚠️  Search returned no results. Check if embeddings were generated correctly.")
else:
    print(f"\n⚠️  FAILED! Documents processed but not added to FAISS index.")
