import pytest
from law.config import DB_PATHS

@pytest.mark.asyncio
async def test_all_shards_exist():
    """Check if all sharded database files exist physically."""
    for key, path in DB_PATHS.items():
        assert path.exists(), f"Shard '{key}' not found at {path}"

@pytest.mark.asyncio
async def test_table_presence(meta_db, statutes_db, precedents_db, decisions_db):
    """Verify that each shard has its required tables."""
    
    async def get_tables(db):
        async with db.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
            return [row['name'] for row in await cursor.fetchall()]

    # meta shard
    assert "scrape_runs" in await get_tables(meta_db)
    
    # statutes shard
    statute_tables = await get_tables(statutes_db)
    assert "statutes" in statute_tables
    assert "admin_rules" in statute_tables
    
    # precedents and decisions shards
    assert "precedents" in await get_tables(precedents_db)
    assert "precedents" in await get_tables(decisions_db)

@pytest.mark.asyncio
async def test_statutes_quality(statutes_db):
    """Check data quality of the statutes table."""
    async with statutes_db.execute("SELECT COUNT(*) as cnt FROM statutes") as cursor:
        row = await cursor.fetchone()
        count = row['cnt']
    
    if count == 0:
        pytest.skip("No statutes in DB yet")

    # Check for empty content
    async with statutes_db.execute("SELECT COUNT(*) as cnt FROM statutes WHERE content IS NULL OR length(content) < 10") as cursor:
        row = await cursor.fetchone()
        assert row['cnt'] == 0, f"Found {row['cnt']} statutes with empty or too short content"

    # Check for required fields
    async with statutes_db.execute("SELECT COUNT(*) as cnt FROM statutes WHERE article_number IS NULL OR law_name IS NULL") as cursor:
        row = await cursor.fetchone()
        assert row['cnt'] == 0, "Found statutes with missing required metadata"

@pytest.mark.asyncio
async def test_admin_rules_quality(statutes_db):
    """Check data quality of the admin_rules table."""
    async with statutes_db.execute("SELECT COUNT(*) as cnt FROM admin_rules") as cursor:
        row = await cursor.fetchone()
        count = row['cnt']
    
    if count == 0:
        pytest.skip("No admin rules in DB yet")

    async with statutes_db.execute("SELECT COUNT(*) as cnt FROM admin_rules WHERE content IS NULL OR length(content) < 10") as cursor:
        row = await cursor.fetchone()
        assert row['cnt'] == 0, f"Found {row['cnt']} admin rules with empty or too short content"

@pytest.mark.asyncio
async def test_precedents_quality(precedents_db, decisions_db):
    """Check data quality of both precedent shards (precedents/decisions)."""
    
    for shard_key, db in [("precedents", precedents_db), ("decisions", decisions_db)]:
        async with db.execute("SELECT COUNT(*) as cnt FROM precedents") as cursor:
            row = await cursor.fetchone()
            count = row['cnt']
        
        if count == 0:
            continue  # Decisions shard might be empty

        # Check for empty content
        async with db.execute("SELECT COUNT(*) as cnt FROM precedents WHERE full_text IS NULL AND summary IS NULL") as cursor:
            row = await cursor.fetchone()
            assert row['cnt'] == 0, f"[{shard_key}] Found precedents with no text content"

@pytest.mark.asyncio
async def test_duplicate_entries(statutes_db):
    """Ensure no duplicate records based on primary unique keys."""
    async with statutes_db.execute("""
        SELECT source_key, article_number, article_title, COUNT(*) as cnt 
        FROM statutes 
        GROUP BY source_key, article_number, article_title 
        HAVING cnt > 1
    """) as cursor:
        dupes = await cursor.fetchall()
        assert len(dupes) == 0, f"Found duplicate statutes: {dupes}"