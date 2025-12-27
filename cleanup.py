import sqlite3
import os

data_dir = "4_data/data_prototype"
db_path = os.path.join(data_dir, "metadata.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("DELETE FROM documents WHERE doc_id IN ('dummy_summary', 'dummy_feeder')")
conn.commit()
conn.close()
print("Dummy data removed.")
