"""SQLite schema definition and database initialization."""

from __future__ import annotations

import logging
import aiosqlite

from law.config import DATA_DIR, DB_PATHS

logger = logging.getLogger(__name__)

# --- Sharded DDLs ---

DDL_META = """
-- Scraping run tracking
CREATE TABLE IF NOT EXISTS scrape_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'running',
    total_records   INTEGER DEFAULT 0,
    checkpoint      TEXT,
    error_message   TEXT
);

-- Integrity verification log
CREATE TABLE IF NOT EXISTS integrity_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name      TEXT NOT NULL,
    record_id       INTEGER NOT NULL,
    checked_at      TEXT NOT NULL,
    hash_match      INTEGER NOT NULL,
    details         TEXT
);
"""

DDL_STATUTES = """
-- Statutes: 형법, 형사소송법, 경찰관직무집행법
CREATE TABLE IF NOT EXISTS statutes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT NOT NULL,
    law_name        TEXT NOT NULL,
    part            TEXT,
    chapter         TEXT,
    section         TEXT,
    subsection      TEXT,
    article_number  TEXT NOT NULL,
    article_title   TEXT,
    content         TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    scraped_at      TEXT NOT NULL,
    scrape_run_id   INTEGER,
    attachments     TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_statutes_unique
    ON statutes(source_key, article_number, article_title);

-- Administrative rules: 경찰수사규칙
CREATE TABLE IF NOT EXISTS admin_rules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT NOT NULL DEFAULT 'generic_admin_rule',
    rule_name       TEXT NOT NULL,
    part            TEXT,
    chapter         TEXT,
    section         TEXT,
    article_number  TEXT NOT NULL,
    article_title   TEXT,
    content         TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    scraped_at      TEXT NOT NULL,
    scrape_run_id   INTEGER,
    attachments     TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_rules_unique
    ON admin_rules(source_key, article_number, article_title);
"""

# Precedents schema used by both 'precedents' and 'decisions' shards
DDL_PRECEDENTS = """
CREATE TABLE IF NOT EXISTS precedents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT NOT NULL,
    case_number     TEXT NOT NULL,
    case_name       TEXT,
    court           TEXT,
    decision_date   TEXT,
    case_type       TEXT DEFAULT '형사',
    holding         TEXT,
    summary         TEXT,
    full_text       TEXT,
    referenced_statutes TEXT,
    referenced_cases    TEXT,
    content_hash    TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    scraped_at      TEXT NOT NULL,
    scrape_run_id   INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_precedents_unique
    ON precedents(source_key, case_number);
"""

DB_DDL_MAP = {
    "meta": DDL_META,
    "statutes": DDL_STATUTES,
    "precedents": DDL_PRECEDENTS,
    "decisions": DDL_PRECEDENTS,
}


async def init_db() -> None:
    """Create all sharded databases and tables if they don't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for db_key, path in DB_PATHS.items():
        ddl = DB_DDL_MAP.get(db_key)
        if not ddl:
            continue

        async with aiosqlite.connect(path) as db:
            await db.executescript(ddl)
            
            # Migration/Adjustment logic per shard
            if db_key == "meta":
                async with db.execute("PRAGMA table_info(scrape_runs)") as cursor:
                    cols = [row[1] for row in await cursor.fetchall()]
                    if "checkpoint" not in cols:
                        await db.execute("ALTER TABLE scrape_runs ADD COLUMN checkpoint TEXT")
            
            elif db_key == "statutes":
                # Check attachments column
                for table in ["statutes", "admin_rules"]:
                    async with db.execute(f"PRAGMA table_info({table})") as cursor:
                        cols = [row[1] for row in await cursor.fetchall()]
                        if "attachments" not in cols:
                            await db.execute(f"ALTER TABLE {table} ADD COLUMN attachments TEXT")
            
            elif db_key in ["precedents", "decisions"]:
                # Check court column constraint
                async with db.execute("PRAGMA table_info(precedents)") as cursor:
                    columns = await cursor.fetchall()
                    court_col = next((c for c in columns if c[1] == "court"), None)
                    if court_col and court_col[3] == 1:  # NOT NULL constraint
                        await db.executescript("""
                            BEGIN TRANSACTION;
                            CREATE TABLE IF NOT EXISTS precedents_new (
                                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                                source_key      TEXT NOT NULL,
                                case_number     TEXT NOT NULL,
                                case_name       TEXT,
                                court           TEXT,
                                decision_date   TEXT,
                                case_type       TEXT DEFAULT '형사',
                                holding         TEXT,
                                summary         TEXT,
                                full_text       TEXT,
                                referenced_statutes TEXT,
                                referenced_cases    TEXT,
                                content_hash    TEXT NOT NULL,
                                source_url      TEXT NOT NULL,
                                scraped_at      TEXT NOT NULL,
                                scrape_run_id   INTEGER
                            );
                            INSERT INTO precedents_new SELECT id, source_key, case_number, case_name, court, decision_date, case_type, holding, summary, full_text, referenced_statutes, referenced_cases, content_hash, source_url, scraped_at, scrape_run_id FROM precedents;
                            DROP TABLE precedents;
                            ALTER TABLE precedents_new RENAME TO precedents;
                            CREATE UNIQUE INDEX IF NOT EXISTS idx_precedents_unique ON precedents(source_key, case_number);
                            COMMIT;
                        """)

            await db.commit()

