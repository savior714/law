import sqlite3

db_path = r'c:\develop\law\data\law_precedents.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT case_number, summary, full_text FROM precedents WHERE source_key='scourt_criminal_precedent' LIMIT 10")
results = cursor.fetchall()
for idx, (case_no, summary, full_text) in enumerate(results):
    print(f"{idx+1}. CASE: {case_no}")
    print(f"   SUMMARY: {summary[:50] if summary else 'None'}...")
    print(f"   FULL_TEXT: {full_text[:50] if full_text else 'None'}...")
conn.close()
