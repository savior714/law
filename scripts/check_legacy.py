import sqlite3
from pathlib import Path

def check_counts():
    db_path = Path('data/law.db')
    if not db_path.exists():
        print("Legacy DB not found.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"{t}: {cursor.fetchone()[0]}")
        
        if t == 'precedents':
            cursor.execute("SELECT source_key, COUNT(*) FROM precedents GROUP BY source_key")
            for sk, count in cursor.fetchall():
                print(f"  - {sk}: {count}")
                
    conn.close()

if __name__ == '__main__':
    check_counts()