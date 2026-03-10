import sqlite3

db_path = r'c:\develop\law\data\law_precedents.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM precedents WHERE source_key='scourt_criminal_precedent'")
print(f"TOTAL: {cursor.fetchone()[0]}")
cursor.execute("SELECT COUNT(*) FROM precedents WHERE source_key='scourt_criminal_precedent' AND (full_text IS NULL OR LENGTH(full_text) < 100)")
print(f"MISSING: {cursor.fetchone()[0]}")
conn.close()
