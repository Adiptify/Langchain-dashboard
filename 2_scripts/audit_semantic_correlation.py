import sqlite3
import json
import os

DB_PATH = '4_data/data_prototype/metadata.db'

def audit_correlation():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    print("="*60)
    print("SEMANTIC CORRELATION AUDIT")
    print("="*60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Query documents to show correlation tags
    cursor.execute("SELECT file_name, doc_type, metadata FROM documents WHERE doc_type IN ('row', 'file_summary', 'text_chunk')")
    rows = cursor.fetchall()

    correlations = {}

    for file_name, doc_type, metadata_json in rows:
        metadata = json.loads(metadata_json)
        tags = metadata.get('context_tags', [])
        
        if not tags:
            continue
            
        for tag in tags:
            tag_clean = tag.strip().upper()
            if tag_clean not in correlations:
                correlations[tag_clean] = set()
            correlations[tag_clean].add(file_name)

    print("\nDISCOVERED SEMANTIC BRIDGES (Shared Entities):")
    bridge_found = False
    for tag, files in correlations.items():
        if len(files) > 1:
            bridge_found = True
            print(f"-> Entity: '{tag}'")
            print(f"   Matches found in: {', '.join(files)}")
    
    if not bridge_found:
        print("- No multi-file bridges found. Check entity extraction logs.")

    print("\nDOCUMENT TAGS (Sample):")
    cursor.execute("SELECT file_name, doc_type, metadata FROM documents ORDER BY doc_id DESC LIMIT 5")
    for r in cursor.fetchall():
        m = json.loads(r[2])
        tags = m.get('context_tags', [])
        print(f"- {r[0]} ({r[1]}): {', '.join(tags) if tags else 'No Tags'}")

    conn.close()

if __name__ == "__main__":
    audit_correlation()
