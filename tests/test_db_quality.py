import pytest
import aiosqlite
from pathlib import Path
from law.config import DB_PATH

@pytest.fixture
async def db():
    if not DB_PATH.exists():
        pytest.skip("Database file does not exist. Run scraping first.")
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        yield conn

@pytest.mark.asyncio
async def test_db_exists():
    assert DB_PATH.exists(), f"Database not found at {DB_PATH}"

@pytest.mark.asyncio
async def test_table_presence(db):
    async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
        tables = [row['name'] for row in await cursor.fetchall()]
    assert "statutes" in tables
    assert "admin_rules" in tables
    assert "scrape_runs" in tables

@pytest.mark.asyncio
async def test_statutes_quality(db):
    async with db.execute("SELECT COUNT(*) as cnt FROM statutes") as cursor:
        row = await cursor.fetchone()
        count = row['cnt']
    
    if count == 0:
        pytest.skip("No statutes in DB yet")

    # Check for empty content
    async with db.execute("SELECT COUNT(*) as cnt FROM statutes WHERE content IS NULL OR length(content) < 10") as cursor:
        row = await cursor.fetchone()
        assert row['cnt'] == 0, f"Found {row['cnt']} statutes with empty or too short content"

    # Check for required fields
    async with db.execute("SELECT COUNT(*) as cnt FROM statutes WHERE article_number IS NULL OR law_name IS NULL") as cursor:
        row = await cursor.fetchone()
        assert row['cnt'] == 0, "Found statutes with missing required metadata"

@pytest.mark.asyncio
async def test_admin_rules_quality(db):
    async with db.execute("SELECT COUNT(*) as cnt FROM admin_rules") as cursor:
        row = await cursor.fetchone()
        count = row['cnt']
    
    if count == 0:
        pytest.skip("No admin rules in DB yet")

    async with db.execute("SELECT COUNT(*) as cnt FROM admin_rules WHERE content IS NULL OR length(content) < 10") as cursor:
        row = await cursor.fetchone()
        assert row['cnt'] == 0, f"Found {row['cnt']} admin rules with empty or too short content"

@pytest.mark.asyncio
async def test_duplicate_entries(db):
    # Verified by UNIQUE INDEX, but let's be sure the data isn't corrupted
    async with db.execute("""
        SELECT source_key, article_number, article_title, COUNT(*) as cnt 
        FROM statutes 
        GROUP BY source_key, article_number, article_title 
        HAVING cnt > 1
    """) as cursor:
        dupes = await cursor.fetchall()
        assert len(dupes) == 0, f"Found duplicate statutes: {dupes}"
