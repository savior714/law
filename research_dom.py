import asyncio
import logging
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        # Criminal Investigation Rule URL
        url = "https://www.law.go.kr/LSW/admRulInfoP.do?admRulSeq=2100000272092&chrClsCd=010201"
        await page.goto(url)
        await asyncio.sleep(5)
        
        # Look for '별표/서식' tab
        # Usually it's the second tab in the left sidebar or top
        tab = await page.query_selector("text='별표/서식'") or await page.query_selector("#tabSms_2")
        if tab:
            print("Found '별표/서식' tab. Clicking...")
            await tab.click()
            try:
                await page.wait_for_selector(".ls_sms_list li, #smsBody li", timeout=10000)
            except:
                print("Timeout waiting for list items.")
            
            items = await page.query_selector_all(".ls_sms_list li, #smsBody li, .ls_sms_list tr, #smsBody tr")
            print(f"Found {len(items)} items in attachments list.")
            for i, item in enumerate(items[:20]):
                text = await item.inner_text()
                html = await item.inner_html()
                # Find links
                links = await item.query_selector_all("a")
                link_titles = [await l.get_attribute("title") for l in links]
                link_hrefs = [await l.get_attribute("href") for l in links]
                
                print(f"Item {i}: {text.strip()[:100]}")
                print(f"  Titles: {link_titles}")
                print(f"  Hrefs: {link_hrefs}")
        else:
            print("Could not find '별표/서식' tab.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
