
import sqlite3
from pathlib import Path

db_paths = {
    "meta": "c:/develop/law/data/law_meta.db",
    "statutes": "c:/develop/law/data/law_statutes.db",
    "precedents": "c:/develop/law/data/law_precedents.db",
    "decisions": "c:/develop/law/data/law_decisions.db",
}

for key, path in db_paths.items():
    if not Path(path).exists():
        print(f"{key}: File not found")
        continue
    
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    print(f"\n--- {key} ({path}) ---")
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for table in tables:
            t_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {t_name}")
            count = cursor.fetchone()[0]
            print(f"  Table: {t_name}, Count: {count}")
    except Exception as e:
        print(f"  Error: {e}")
    finally:
        conn.close()
