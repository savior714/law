"""SQLite schema definition and database initialization."""

from __future__ import annotations

import aiosqlite

from law.config import DATA_DIR, DB_PATH

DDL = """
-- Scraping run tracking
CREATE TABLE IF NOT EXISTS scrape_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'running',
    total_records   INTEGER DEFAULT 0,
    error_message   TEXT
);

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
    scrape_run_id   INTEGER REFERENCES scrape_runs(id),
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
    scrape_run_id   INTEGER REFERENCES scrape_runs(id),
    attachments     TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_rules_unique
    ON admin_rules(source_key, article_number, article_title);

-- Precedents: law.go.kr + scourt portal
CREATE TABLE IF NOT EXISTS precedents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key      TEXT NOT NULL,
    case_number     TEXT NOT NULL,
    case_name       TEXT,
    court           TEXT NOT NULL,
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
    scrape_run_id   INTEGER REFERENCES scrape_runs(id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_precedents_unique
    ON precedents(source_key, case_number);

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


async def init_db() -> None:
    """Create the database and all tables if they don't exist, and handle migrations."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(DDL)
        
        # Check if 'attachments' column exists in 'statutes'
        async with db.execute("PRAGMA table_info(statutes)") as cursor:
            cols = [row[1] for row in await cursor.fetchall()]
            if "attachments" not in cols:
                await db.execute("ALTER TABLE statutes ADD COLUMN attachments TEXT")
                
        # Check if 'attachments' column exists in 'admin_rules'
        async with db.execute("PRAGMA table_info(admin_rules)") as cursor:
            cols = [row[1] for row in await cursor.fetchall()]
            if "attachments" not in cols:
                await db.execute("ALTER TABLE admin_rules ADD COLUMN attachments TEXT")
        
        # Recreate unique indexes for statutes to include title
        await db.execute("DROP INDEX IF EXISTS idx_statutes_unique")
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_statutes_unique ON statutes(source_key, article_number, article_title)")

        # Recreate unique indexes for admin_rules to include title
        await db.execute("DROP INDEX IF EXISTS idx_admin_rules_unique")
        await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_admin_rules_unique ON admin_rules(source_key, article_number, article_title)")

        await db.commit()
