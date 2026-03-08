
import asyncio
from law.scrapers.law_statute import StatuteScraper
from law.scrapers.law_admin_rule import AdminRuleScraper
from law.config import SOURCES

async def test_all():
    for key, info in SOURCES.items():
        print(f"\n--- Testing {info['name']} ---")
        if info['scraper'] == 'law_statute':
            scraper = StatuteScraper(key)
        else:
            scraper = AdminRuleScraper(key)
            
        await scraper.init_browser()
        try:
            count = 0
            async for article in scraper.scrape():
                print(f"[{article.article_number}] {article.article_title}")
                count += 1
                if count >= 3: break
            print(f"Result: {count} articles found.")
        except Exception as e:
            print(f"FAILED: {e}")
        finally:
            await scraper.close()

if __name__ == "__main__":
    asyncio.run(test_all())
