import pytest
import pytest_asyncio
from law.db.repository import Repository
from law.config import DB_PATHS

@pytest_asyncio.fixture
async def repo():
    """Provides a connected Repository instance manageing all shards."""
    # Ensure all DB files exist before connecting
    for key, path in DB_PATHS.items():
        if not path.exists():
            pytest.skip(f"Database shard '{key}' not found at {path}. Run scraping first.")
    
    r = Repository()
    await r.connect()
    yield r
    await r.close()

@pytest_asyncio.fixture
async def meta_db(repo):
    """Fixture for law_meta.db connection (scrape_runs)."""
    return repo.get_db("meta")

@pytest_asyncio.fixture
async def statutes_db(repo):
    """Fixture for law_statutes.db connection (statutes, admin_rules)."""
    return repo.get_db("statutes")

@pytest_asyncio.fixture
async def precedents_db(repo):
    """Fixture for law_precedents.db connection (precedents)."""
    return repo.get_db("precedents")

@pytest_asyncio.fixture
async def decisions_db(repo):
    """Fixture for law_decisions.db connection (헌재/해석례 precedents)."""
    return repo.get_db("decisions")