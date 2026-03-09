import asyncio
import logging
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))

from law.scrapers.scourt_precedent import ScourtPrecedentScraper

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    scraper = ScourtPrecedentScraper()
    print(">>> Initializing browser...")
    await scraper.init_browser(headless=True)
    
    try:
        print(">>> Starting scrape (will stop after 2 items)...")
        count = 0
        async for prec in scraper.scrape():
            print(f"  [SUCCESS] {prec.case_number}: {prec.case_name}")
            if prec.full_text:
                print(f"    Body length: {len(prec.full_text)}")
            else:
                print("    [WARNING] No full text (API call might have failed)")
            
            count += 1
            if count >= 2:
                break
        
        if count == 0:
            print(">>> [ERROR] No items scraped.")
    except Exception as e:
        print(f">>> [FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.close()
        print(">>> Browser closed.")

if __name__ == "__main__":
    asyncio.run(main())
