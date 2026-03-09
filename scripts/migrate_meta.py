import sqlite3
import os
from pathlib import Path

def migrate():
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / 'data'
    legacy_db = data_dir / 'law.db'
    meta_db = data_dir / 'law_meta.db'

    if not legacy_db.exists():
        print(f"Legacy DB not found at {legacy_db}")
        return

    print(f"Connecting to {legacy_db} and {meta_db}...")
    
    conn = sqlite3.connect(meta_db)
    cursor = conn.cursor()

    # Attach legacy DB
    cursor.execute(f"ATTACH DATABASE '{legacy_db}' AS legacy")

    tables = ['scrape_runs', 'integrity_log']
    
    for table in tables:
        print(f"Migrating {table}...")
        try:
            # Check if source table exists in legacy
            cursor.execute(f"SELECT name FROM legacy.sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                print(f"Table {table} not found in legacy DB. Skipping.")
                continue

            # Clear target first (just in case this is a retry)
            cursor.execute(f"DELETE FROM {table}")
            
            # Copy data
            cursor.execute(f"INSERT INTO {table} SELECT * FROM legacy.{table}")
            conn.commit()
            
            # Verify count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ Migrated {count} rows into {table}")
        except Exception as e:
            print(f"❌ Error migrating {table}: {e}")

    cursor.execute("DETACH DATABASE legacy")
    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()