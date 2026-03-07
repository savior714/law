
import asyncio
from law.scrapers.law_statute import StatuteScraper

async def debug_scrape():
    scraper = StatuteScraper("police_investigation_rules")
    await scraper.init_browser()
    try:
        articles = []
        async for article in scraper.scrape():
            articles.append(article)
        
        print(f"Total found: {len(articles)}")
        print("First 20 articles found (in order):")
        for i, a in enumerate(articles[:20]):
            print(f"{i+1:02d}: {a.article_number} ({a.article_title}) - {a.content[:50]}...")
        
        counts = {}
        for a in articles:
            counts[a.article_number] = counts.get(a.article_number, 0) + 1
        
        dups = {k: v for k, v in counts.items() if v > 1}
        print(f"Duplicates (article_number): {dups}")
        
        expected_found = any("목적" in (a.article_title or "") for a in articles)
        print(f"Is '목적' present in titles?: {expected_found}")
            
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(debug_scrape())
