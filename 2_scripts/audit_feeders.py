import sqlite3
import os

def audit_feeders():
    db_path = '4_data/data_prototype/metadata.db'
    if not os.path.exists(db_path):
        print(f"Error: DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("="*60)
    print("DATABASE FEEDER AUDIT")
    print("="*60)
    
    import json
    
    # List unique feeders
    cursor.execute("SELECT metadata FROM documents WHERE doc_type = 'feeder_data'")
    rows = cursor.fetchall()
    
    feeders = set()
    locations = set()
    for row in rows:
        meta = json.loads(row[0])
        if 'feeder' in meta: feeders.add(meta['feeder'])
        if 'location' in meta: locations.add(meta['location'])
    
    print(f"\nUNIQUE FEEDERS (Found {len(feeders)}):")
    for f in sorted(list(feeders)):
        print(f" - {f}")
        
    print(f"\nUNIQUE LOCATIONS (Found {len(locations)}):")
    for l in sorted(list(locations)):
        print(f" - {l}")

    conn.close()

if __name__ == "__main__":
    audit_feeders()
