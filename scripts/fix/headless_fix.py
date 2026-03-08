
import asyncio
import logging
from law.db.schema import init_db
from law.db.repository import Repository
from law.config import SOURCES
from law.scrapers.law_statute import StatuteScraper
from law.scrapers.law_admin_rule import AdminRuleScraper
from law.export.builder import build_dataset

logging.basicConfig(level=logging.INFO)

async def headless_run():
    print("Initialising DB...")
    await init_db()
    repo = Repository()
    await repo.connect()
    
    try:
        # 1. Scrape only police_investigation_rules for verification
        target = "police_investigation_rules"
        src = SOURCES[target]
        print(f"Scraping {target}...")
        
        run_id = await repo.start_run(target)
        scraper = StatuteScraper(target)
        
        count = 0
        await scraper.init_browser()
        async for record in scraper.scrape():
            await repo.upsert_statute(record, src["url"], run_id)
            count += 1
            if count % 10 == 0: print(f"  {count}...")
        
        await scraper.close()
        await repo.finish_run(run_id, total=count)
        print(f"Done scraping {target}: {count} articles.")
        
        # 2. Build dataset
        print("Building dataset...")
        await build_dataset(repo)
        print("Dataset built.")
        
    finally:
        await repo.close()

if __name__ == "__main__":
    asyncio.run(headless_run())
