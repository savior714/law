import asyncio
import logging
from playwright.async_api import async_playwright

async def debug_pagination():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 900})
        page = await context.new_page()
        
        url = "https://www.law.go.kr/precSc.do?menuId=7&subMenuId=47&tabMenuId=213&query="
        await page.goto(url, wait_until="domcontentloaded")
        
        # search "형사" just like the scraper
        inner_input = await page.query_selector("#innerQuery")
        if inner_input:
            await inner_input.fill("형사")
            await inner_input.press("Enter")
            await asyncio.sleep(4)
        
        # We will retrieve the paging block and figure out how to click next
        for i in range(1, 4):
            print(f"--- Page {i} ---")
            
            paging_html = await page.evaluate("() => { const el = document.querySelector('.paging'); return el ? el.outerHTML : 'Not found'; }")
            print("Paging HTML:")
            print(paging_html)
            
            # JS logic to click next page
            clicked = await page.evaluate("""() => {
                const currentLi = document.querySelector(".paging ol li.on");
                if (currentLi && currentLi.nextElementSibling) {
                    const a = currentLi.nextElementSibling.querySelector("a");
                    if (a) {
                        a.click();
                        return true;
                    }
                }
                const nextGrp = document.querySelector(".paging a img[alt*='다음']");
                if (nextGrp) {
                    nextGrp.parentElement.click();
                    return true;
                }
                return false;
            }""")
            print("Clicked next:", clicked)
            await asyncio.sleep(2)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_pagination())
