import asyncio
import logging
from law.db.repository import Repository
from law.scrapers.law_decision_ext import ConstitutionalScraper
from law.config import SOURCES

logging.basicConfig(level=logging.INFO)

async def main():
    source_key = "law_go_kr_constitutional"
    src = SOURCES[source_key]
    scraper = ConstitutionalScraper()
    
    repo = Repository()
    await repo.connect()
    run_id = await repo.start_run(source_key)
    
    print(f">>> Scraping {src.name} (Constitutional Cases)...")
    await scraper.init_browser(headless=True)
    
    count = 0
    try:
        async for record in scraper.scrape():
            await repo.upsert_precedent(record, src.url, run_id)
            count += 1
            if count >= 5: # 5건만 샘플링
                break
    finally:
        await scraper.close()
        await repo.finish_run(run_id, total=count)
        await repo.close()
        print(f">>> Finished: {count} constitutional cases saved.")

if __name__ == "__main__":
    asyncio.run(main())