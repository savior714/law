
import asyncio
from playwright.async_api import async_playwright

async def debug_page():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        # The URL that failed
        url = "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=276410"
        print(f"DEBUG: Navigating to {url}")
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(5)  # give it extra time to render
            
            ls_bdy = await page.query_selector("#lsBdy")
            body_content = await page.query_selector("#bodyContent")
            
            print(f"DEBUG: #lsBdy found: {ls_bdy is not None}")
            print(f"DEBUG: #bodyContent found: {body_content is not None}")
            
            if ls_bdy:
                text = await ls_bdy.inner_text()
                print(f"DEBUG: #lsBdy length: {len(text)}")
            if body_content:
                text = await body_content.inner_text()
                print(f"DEBUG: #bodyContent length: {len(text)}")
            
            # Extract current URL
            print(f"DEBUG: Final URL: {page.url}")
            
            if not ls_bdy and not body_content:
                # This is the fail case
                print("DEBUG: Neither found. Listing some IDs on the page:")
                ids = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('[id]')).map(el => el.id).slice(0, 10);
                }""")
                print(f"DEBUG: First 10 IDs: {ids}")
                
        except Exception as e:
            print(f"EXCEPTION: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_page())
