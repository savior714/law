
import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        try:
            await page.goto("https://www.law.go.kr/LSW/lsInfoP.do?lsId=013976", timeout=30000)
            await page.wait_for_selector(".ls_knm", timeout=10000)
            title1 = await page.inner_text(".ls_knm")
            print(f"URL 1 (013976): {title1.strip()}")
        except Exception as e:
            print(f"URL 1 error: {e}")
            
        try:
            await page.goto("https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=276410", timeout=30000)
            await page.wait_for_selector(".ls_knm", timeout=10000)
            title2 = await page.inner_text(".ls_knm")
            print(f"URL 2 (276410): {title2.strip()}")
        except Exception as e:
            print(f"URL 2 error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check())
