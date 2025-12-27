import sqlite3
import json
import os
import sys

# Add core to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '1_core')))

data_dir = "4_data/data_prototype"
db_path = os.path.join(data_dir, "metadata.db")

def add_dummy_data():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables if not exist (though they should)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id TEXT PRIMARY KEY,
            content TEXT,
            metadata TEXT,
            doc_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    summary_content = "The total plant energy consumption for July 2024 is 125,450,000 KWH. The highest peak was on July 15th."
    summary_metadata = {
        "total": 125450000,
        "month": "July 2024",
        "peak_day": "2024-07-15"
    }
    
    cursor.execute("INSERT OR REPLACE INTO documents (doc_id, content, metadata, doc_type) VALUES (?, ?, ?, ?)", 
                   ("dummy_summary", summary_content, json.dumps(summary_metadata), "plant_summary"))
    
    feeder_data = "Feeder Panel-1 consumption is 50,000 KWH."
    feeder_metadata = {"feeder": "Panel-1", "value": 50000}
    cursor.execute("INSERT OR REPLACE INTO documents (doc_id, content, metadata, doc_type) VALUES (?, ?, ?, ?)", 
                   ("dummy_feeder", feeder_data, json.dumps(feeder_metadata), "feeder_data"))
    
    conn.commit()
    conn.close()
    print("Dummy data added.")

if __name__ == "__main__":
    add_dummy_data()
