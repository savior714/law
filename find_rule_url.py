import asyncio
from playwright.async_api import async_playwright

async def find_rule_url():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        query = "경찰수사규칙"
        url = f"https://www.law.go.kr/lsSc.do?query={query}"
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(5)
        
        # Get the first result link
        link = await page.query_selector("dt > a[href*='lsInfoP.do']")
        if link:
            href = await link.get_attribute("href")
            print(f"FOUND_URL: {href}")
            title = await link.inner_text()
            print(f"FOUND_TITLE: {title}")
        else:
            print("NOT_FOUND")
            # Try to see what's on the page
            content = await page.content()
            with open("debug_search.html", "w", encoding="utf-8") as f:
                f.write(content)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_rule_url())
