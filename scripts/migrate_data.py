import sqlite3
import os
from pathlib import Path
import json

# Manual mapping logic based on SOURCES (config.py is not imported to avoid confusion/circulars)
PRE_SOURCES = ['scourt_criminal_precedent', 'law_go_kr_precedent']
DEC_SOURCES = ['law_go_kr_constitutional', 'law_go_kr_interpretation', 'law_go_kr_admin_appeal']

def migrate_data():
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / 'data'
    legacy_db = data_dir / 'law.db'
    statutes_db = data_dir / 'law_statutes.db'
    precedents_db = data_dir / 'law_precedents.db'
    decisions_db = data_dir / 'law_decisions.db'

    if not legacy_db.exists():
        print(f"Legacy DB not found at {legacy_db}")
        return

    conn_l = sqlite3.connect(legacy_db)
    cursor_l = conn_l.cursor()

    # 1. Statutes & Admin Rules
    c_s = sqlite3.connect(statutes_db)
    print(f"Migrating statutes/admin_rules to {statutes_db}...")
    c_s.execute(f"ATTACH DATABASE '{legacy_db}' AS legacy")
    
    # statutes
    c_s.execute("DELETE FROM statutes")
    c_s.execute("INSERT INTO statutes SELECT * FROM legacy.statutes")
    print(f"✅ Migrated {c_s.execute('SELECT COUNT(*) FROM statutes').fetchone()[0]} statutes.")
    
    # admin_rules
    c_s.execute("DELETE FROM admin_rules")
    c_s.execute("INSERT INTO admin_rules SELECT * FROM legacy.admin_rules")
    print(f"✅ Migrated {c_s.execute('SELECT COUNT(*) FROM admin_rules').fetchone()[0]} admin_rules.")
    
    c_s.commit()
    c_s.execute("DETACH DATABASE legacy")
    c_s.close()

    # 2. Precedents (Splitting)
    print("Migrating precedents (routing by source_key)...")
    
    # Precedents
    c_p = sqlite3.connect(precedents_db)
    c_p.execute(f"ATTACH DATABASE '{legacy_db}' AS legacy")
    c_p.execute("DELETE FROM precedents")
    # Using source_key list to route
    keys_str = ",".join([f"'{k}'" for k in PRE_SOURCES])
    c_p.execute(f"INSERT INTO precedents SELECT * FROM legacy.precedents WHERE source_key IN ({keys_str})")
    print(f"✅ Migrated {c_p.execute('SELECT COUNT(*) FROM precedents').fetchone()[0]} court precedents.")
    c_p.commit()
    c_p.execute("DETACH DATABASE legacy")
    c_p.close()

    # Decisions
    c_d = sqlite3.connect(decisions_db)
    c_d.execute(f"ATTACH DATABASE '{legacy_db}' AS legacy")
    c_d.execute("DELETE FROM precedents")
    # Using source_key list to route
    keys_str_dec = ",".join([f"'{k}'" for k in DEC_SOURCES])
    if DEC_SOURCES:
        c_d.execute(f"INSERT INTO precedents SELECT * FROM legacy.precedents WHERE source_key IN ({keys_str_dec})")
    print(f"✅ Migrated {c_d.execute('SELECT COUNT(*) FROM precedents').fetchone()[0]} decisions (constitutional, etc).")
    c_d.commit()
    c_d.execute("DETACH DATABASE legacy")
    c_d.close()

    conn_l.close()
    print("Phase 3 Migration complete.")

if __name__ == '__main__':
    migrate_data()