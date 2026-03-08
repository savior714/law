
import asyncio
from playwright.async_api import async_playwright

async def debug_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        url = "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=276410"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        
        # Check for common containers
        ls_bdy = await page.query_selector("#lsBdy")
        body_content = await page.query_selector("#bodyContent")
        
        print(f"#lsBdy found: {ls_bdy is not None}")
        print(f"#bodyContent found: {body_content is not None}")
        
        if ls_bdy:
            text = await ls_bdy.inner_text()
            print(f"#lsBdy text length: {len(text)}")
        if body_content:
            text = await body_content.inner_text()
            print(f"#bodyContent text length: {len(text)}")
            
        # Capture a bit of HTML if none found
        if not ls_bdy and not body_content:
            html = await page.content()
            print("HTML Snippet (first 1000 chars):")
            print(html[:1000])
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page())
