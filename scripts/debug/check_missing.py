import sqlite3
import os

db_path = r'c:\develop\law\data\law_precedents.db'
if not os.path.exists(db_path):
    print(f"DB not found: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT case_number, full_text FROM precedents WHERE source_key='scourt_criminal_precedent' AND (full_text IS NULL OR LENGTH(full_text) < 100)")
results = cursor.fetchall()
for idx, (case_no, text) in enumerate(results):
    print(f"{idx+1}. CASE: {case_no} | TEXT LEN: {len(text) if text else 'None'} | CONTENT: {text}")
conn.close()
