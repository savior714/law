
import asyncio
import logging
from law.db.repository import Repository
from law.scrapers.law_decision_ext import InterpretationScraper, AdminAppealScraper
from law.config import SOURCES

logging.basicConfig(level=logging.INFO)

async def scrape_sample(source_key, scraper_cls, count_limit=3):
    src = SOURCES[source_key]
    scraper = scraper_cls()
    
    repo = Repository()
    await repo.connect()
    run_id = await repo.start_run(source_key)
    
    print(f"\n>>> Scraping {src.name} (Sample)...")
    await scraper.init_browser(headless=True)
    
    count = 0
    try:
        async for record in scraper.scrape():
            await repo.upsert_precedent(record, src.url, run_id)
            count += 1
            if count >= count_limit:
                break
    except Exception as e:
        print(f"Error scraping {source_key}: {e}")
    finally:
        await scraper.close()
        await repo.finish_run(run_id, total=count)
        await repo.close()
        print(f">>> Finished {source_key}: {count} records saved.")

async def main():
    # 5.3 Interpretation
    await scrape_sample("law_go_kr_interpretation", InterpretationScraper, 3)
    # 5.4 Admin Appeal
    await scrape_sample("law_go_kr_admin_appeal", AdminAppealScraper, 3)

if __name__ == "__main__":
    asyncio.run(main())
