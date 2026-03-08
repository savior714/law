import asyncio
import logging
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from law.scrapers.law_statute import StatuteScraper
from law.scrapers.law_admin_rule import AdminRuleScraper

async def test_statute():
    print("Testing StatuteScraper (Police Investigation Rules)...")
    scraper = StatuteScraper("police_investigation_rules")
    await scraper.init_browser(headless=True)
    try:
        count = 0
        async for article in scraper.scrape():
            print(f"  Extracted: {article.article_number} {article.article_title}")
            count += 1
            if count >= 3: break
        print(f"StatuteScraper test: {'SUCCESS' if count > 0 else 'FAILED'}")
    finally:
        await scraper.close()

async def test_admin_rule():
    print("\nTesting AdminRuleScraper (Crime Investigation Rules)...")
    scraper = AdminRuleScraper("crime_investigation_rules")
    await scraper.init_browser(headless=True)
    try:
        count = 0
        async for article in scraper.scrape():
            print(f"  Extracted: {article.article_number} {article.article_title}")
            count += 1
            if count >= 3: break
        print(f"AdminRuleScraper test: {'SUCCESS' if count > 0 else 'FAILED'}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_statute())
    asyncio.run(test_admin_rule())
