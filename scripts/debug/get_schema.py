import sqlite3
conn = sqlite3.connect('c:/develop/law/data/law_precedents.db')
row = conn.execute('SELECT sql FROM sqlite_master WHERE name="precedents"').fetchone()
print(row[0] if row else 'Table not found')
conn.close()