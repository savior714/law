import asyncio
import sys
from playwright.async_api import async_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

async def find_rule():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        query = "경찰수사규칙"
        url = f"https://www.law.go.kr/lsSc.do?query={query}"
        await page.goto(url, wait_until="networkidle")
        await asyncio.sleep(5)
        
        # Look for the link that contains specific text and click it
        # Based on previous output, text is '2. 경찰수사규칙'
        target_selector = "a:has-text('2.  경찰수사규칙')"
        link = await page.query_selector(target_selector)
        if link:
            # Get the onclick or href
            onclick = await link.get_attribute("onclick")
            print(f"ONCLICK: {onclick}")
            # Alternatively, just click it
            await link.click()
            await asyncio.sleep(5)
            # The page might open in a new window/tab? 
            # Or it might change the URL of the main page or an iframe.
            print(f"Main Page URL after click: {page.url}")
            
            # If it opens a new page
            if len(browser.contexts[0].pages) > 1:
                new_page = browser.contexts[0].pages[-1]
                print(f"NEW_PAGE URL: {new_page.url}")
        else:
            print("TARGET_LINK_NOT_FOUND")
            # Try a broader search
            links = await page.query_selector_all("a")
            for a in links:
                t = await a.inner_text()
                if "경찰수사규칙" in t and "시행 2025" in t:
                    onclick = await a.get_attribute("onclick")
                    print(f"CANDIDATE: {t.strip()} -> {onclick}")
                    await a.click()
                    await asyncio.sleep(5)
                    print(f"URL after CANDIDATE click: {page.url}")
                    if len(browser.contexts[0].pages) > 1:
                        print(f"NEW_PAGE URL: {browser.contexts[0].pages[-1].url}")
                    break

        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_rule())
