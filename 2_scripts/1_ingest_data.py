import sys
import os
import time
from typing import List

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../1_core')))

from smart_preprocessor import JSWEnergyPreprocessor
from embedding_store import EmbeddingStore
import ingestion_pipeline

print("\n" + "="*60)
print("SMART MULTI-FORMAT DATA INGESTION")
print("="*60)

# Paths
data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../4_data'))
prototype_dir = os.path.join(data_dir, 'data_prototype')

# Ensure directories exist
os.makedirs(os.path.join(prototype_dir, "indexes"), exist_ok=True)

# Clean old data (Optional: set to False if you want incremental)
RESET_DB = True
    print("\n🧹 Clearing old database...")
    files_to_clean = [
        os.path.join(prototype_dir, 'indexes', 'faiss.index'),
        os.path.join(prototype_dir, 'indexes', 'id_map.json'),
        os.path.join(prototype_dir, 'metadata.db')
    ]
    for f in files_to_clean:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"   Removed: {os.path.basename(f)}")
            except Exception as e:
                print(f"   🚨 CRITICAL ERROR: Could not remove {os.path.basename(f)}: {e}")
                print("   This usually means the AI Dashboard server or a SQLite viewer is currently using the file.")
                print("   PLEASE STOP THE AI SERVER and run this script again.")
                sys.exit(1)

# Scan for files
supported_extensions = ('.xlsx', '.xls', '.csv', '.pdf', '.docx', '.txt', '.md', '.log')
files_to_process = []

print(f"\n📂 Scanning directory: {data_dir}")
for root, dirs, files in os.walk(data_dir):
    for file in files:
        if file.lower().endswith(supported_extensions):
            files_to_process.append(os.path.join(root, file))

if not files_to_process:
    print("❌ No supported files found in the data directory.")
    sys.exit(0)

print(f"🔍 Found {len(files_to_process)} files to process.")

all_documents = []
start_time = time.time()

# Pre-initialize specialized processors
jsw_processor = JSWEnergyPreprocessor()

print("\n⚙️  Applying Logic-Based Preprocessing:")
print("   - Hierarchical Tiering (Total > Incomer > Feeder)")
print("   - Neighbor-Date Mapping (Fixes 'Difference.X' issues)")
print("   - De-duplication of documents")

for file_path in files_to_process:
    file_name = os.path.basename(file_path)
    file_id = f"file_{int(time.time())}_{file_name}"
    
    print(f"\n📄 Processing: {file_name}")
    try:
        # ROUTING LOGIC
        # 1. Specialized Industrial Report Handling (Hierarchical)
        is_hierarchical_report = file_name.lower().endswith(('.xlsx', '.xls')) and \
                       any(k in file_name.upper() for k in ['ENERGY', 'CONSUMPTION', 'MHS', 'REPORT', 'WATER', 'FLOW', 'UTILITY', 'PROD'])
        
        if is_hierarchical_report:
            print(f"   ✨ Routing to Specialized Industrial Preprocessor...")
            file_docs = jsw_processor.process_file(file_path)
        else:
            # 2. General Smart Ingestion (PDF, DOCX, TXT, CSV, generic Excel)
            print(f"   🧠 Routing to General Smart Ingestion...")
            file_docs = ingestion_pipeline.ingest_file(file_path, file_id=file_id)
            
        if file_docs:
            print(f"   ✅ Extracted {len(file_docs)} document units.")
            all_documents.extend(file_docs)
        else:
            print(f"   ⚠️  No content extracted from {file_name}.")
            
    except Exception as e:
        print(f"   ❌ Error processing {file_name}: {e}")

process_time = time.time() - start_time

if not all_documents:
    print("\n❌ No documents were extracted from any file. Check the logs.")
    sys.exit(1)

# Ingest into store
print(f"\n💾 Adding {len(all_documents)} total documents to embedding store...")
embed_start = time.time()
es = EmbeddingStore()
es.add_documents(all_documents)
embed_time = time.time() - embed_start

if es.faiss_index:
    print("\n" + "="*60)
    print("INGESTION COMPLETE!")
    print("="*60)
    print(f"统计 Statistics:")
    print(f"   - Files Processed: {len(files_to_process)}")
    print(f"   - Total Documents: {es.faiss_index.ntotal}")
    print(f"   - Processing Time: {process_time:.2f}s")
    print(f"   - Embedding Time:  {embed_time:.2f}s")
    print(f"   - AVG Time/Doc:    {(process_time + embed_time) / len(all_documents):.4f}s")
    
    print("\n📝 Sample Summary Documents:")
    summary_docs = [d for d in all_documents if d.doc_type in ['plant_summary', 'monthly_total']]
    for i, doc in enumerate(summary_docs[:5], 1):
        print(f"\n{i}. [{doc.doc_type}] {doc.file_name}:")
        print(f"   {doc.content[:150]}...")

    print(f"\n🔍 Final Verification Search...")
    results = es.search("energy overview", k=3)
    if results:
        print(f"   Top result: [{results[0]['metadata'].get('doc_type', 'unknown')}] {results[0]['content'][:120]}...")
else:
    print(f"\n⚠️  FAILED! Documents processed but not added to FAISS index.")
