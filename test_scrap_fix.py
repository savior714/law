
import asyncio
from playwright.async_api import async_playwright
from law.scrapers.law_statute import StatuteScraper
from law.config import SOURCES

async def test_scrap():
    scraper = StatuteScraper("police_investigation_rules")
    await scraper.init_browser()
    try:
        count = 0
        async for article in scraper.scrape():
            print(f"[{article.article_number}] {article.article_title}")
            count += 1
            if count >= 5: break
        print(f"Total scraped: {count}")
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(test_scrap())
