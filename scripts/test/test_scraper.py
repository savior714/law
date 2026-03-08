import asyncio
import re
from pathlib import Path
from bs4 import BeautifulSoup
from law.scrapers.law_statute import StatuteScraper
from law.config import SOURCES

async def test_single_scrape():
    source_key = "police_duties_act"
    scraper = StatuteScraper(source_key)
    
    print(f"Initializing for {source_key}...")
    await scraper.init_browser(headless=True)
    
    try:
        # Navigate
        await scraper.page.goto(SOURCES[source_key]["url"], wait_until="domcontentloaded")
        await asyncio.sleep(3) # Wait for AJAX
        
        # Get content
        html = await scraper.page.content()
        soup = BeautifulSoup(html, "lxml")
        
        # Select body
        from law.config import SELECTORS_LAW
        body_el = soup.select_one(SELECTORS_LAW["law_body"]) or soup.select_one(SELECTORS_LAW["body_content"])
        
        if not body_el:
            print("Body not found!")
            return

        raw_text = body_el.get_text("\n")
        Path("data/debug_raw.txt").write_text(raw_text, encoding="utf-8")
        print(f"Raw text (len {len(raw_text)}) saved to data/debug_raw.txt")
        
        # Split test
        parts = re.split(r"(?=제\d+조(?:의\d+)?\s*[\(（])", raw_text)
        print(f"Split into {len(parts)} parts.")
        
        for i, part in enumerate(parts[:5]):
            print(f"\n--- Part {i} (len {len(part)}) ---")
            print(part[:200].strip())
            
    finally:
        await scraper.close()

if __name__ == "__main__":
    asyncio.run(test_single_scrape())
