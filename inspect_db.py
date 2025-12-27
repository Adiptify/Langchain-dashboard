import sqlite3
import os
import json

data_dir = "4_data/data_prototype"
db_path = os.path.join(data_dir, "metadata.db")

def inspect_db():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get counts by doc_type
    cursor.execute("SELECT doc_type, COUNT(*) FROM documents GROUP BY doc_type")
    counts = cursor.fetchall()
    print("Document counts by type:")
    for doc_type, count in counts:
        print(f"  {doc_type}: {count}")

    # Inspect plant_summary
    cursor.execute("SELECT doc_id, content, metadata FROM documents WHERE doc_type = 'plant_summary'")
    summaries = cursor.fetchall()
    print("\nPlant Summaries:")
    for doc_id, content, metadata in summaries:
        print(f"  ID: {doc_id}")
        print(f"  Content: {content}")
        print(f"  Metadata: {metadata}")

    # Sample feeder_data
    cursor.execute("SELECT content FROM documents WHERE doc_type = 'feeder_data' LIMIT 3")
    feeders = cursor.fetchall()
    print("\nSample Feeder Data:")
    for (content,) in feeders:
        print(f"  {content}")

    conn.close()

if __name__ == "__main__":
    inspect_db()
