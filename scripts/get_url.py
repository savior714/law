import asyncio
from playwright.async_api import async_playwright

async def get_exact_url():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Go to search result directly
        query = "경찰수사규칙"
        await page.goto(f"https://www.law.go.kr/lsSc.do?query={query}", wait_until="networkidle")
        await asyncio.sleep(5)
        
        print(f"Current URL: {page.url}")
        
        # Look for all matches
        hits = await page.query_selector_all("dt > a")
        for hit in hits:
            txt = await hit.inner_text()
            href = await hit.get_attribute("href")
            print(f"HIT: {txt} -> {href}")
            
        # Try to find exactly '경찰수사규칙' ministerial ordinance
        # It's usually the first hit in statutes section
        target = await page.query_selector("dt:has-text('경찰수사규칙') > a")
        if target:
            href = await target.get_attribute("href")
            print(f"TARGET_HREF: {href}")
            # The href might be 'javascript:f_lsInfoP('013953', '...')'
            # Let's extract IDs from javascript calls
            import re
            match = re.search(r"f_lsInfoP\('(\d+)',\s*'(\d+)'\)", href)
            if match:
                lsId = match.group(1)
                lsiSeq = match.group(2)
                print(f"EXTRACTOR: lsId={lsId}, lsiSeq={lsiSeq}")
                print(f"FINAL_URL: https://www.law.go.kr/LSW/lsInfoP.do?lsId={lsId}&lsiSeq={lsiSeq}")
        else:
            print("NO_TARGET_FOUND")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_exact_url())
