import asyncio
import json
from law.scrapers.law_admin_rule import AdminRuleScraper

async def debug_admin_rule():
    scraper = AdminRuleScraper()
    results = {}
    try:
        await scraper.init_browser(headless=True)
        results["url"] = scraper.source_url
        await scraper.page.goto(scraper.source_url, wait_until="networkidle")
        await asyncio.sleep(5)
        
        # Get all relevant element info
        elements = await scraper.page.evaluate("""() => {
            const data = [];
            document.querySelectorAll('a, button, li, ul').forEach(el => {
                const txt = el.innerText.trim();
                if (txt.includes('본문') || txt.includes('별표') || el.id.includes('tab') || el.id.includes('View')) {
                    data.push({
                        text: txt,
                        id: el.id,
                        tagName: el.tagName,
                        className: el.className
                    });
                }
            });
            return data;
        }""")
        results["elements"] = elements
        
        # Take a screenshot to see where we are
        await scraper.page.screenshot(path="data/debug_admin_tabs.png")
        results["screenshot"] = "data/debug_admin_tabs.png"
        
    except Exception as e:
        results["error"] = str(e)
    finally:
        await scraper.close()
        with open("data/debug_tabs_result.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    asyncio.run(debug_admin_rule())
