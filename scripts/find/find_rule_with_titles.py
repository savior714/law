import asyncio
from playwright.async_api import async_playwright

async def find_rule_with_titles():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Direct lsw search
        query = "경찰수사규칙"
        url = f"https://www.law.go.kr/lsSc.do?query={query}"
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(5)
        
        # Results are usually inside an iframe with id #ifrmLS
        # or it might be just on the page. Let's see all 'a' tags.
        all_a = await page.query_selector_all("a")
        for a in all_a:
            t = await a.inner_text()
            h = await a.get_attribute("href")
            if t and "경찰수사규칙" in t:
                print(f"FOUND: [{t}] href: {h}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_rule_with_titles())
