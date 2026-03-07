
import asyncio
from playwright.async_api import async_playwright

async def check_urls():
    urls = [
        ("경찰수사규칙?", "https://www.law.go.kr/LSW/lsInfoP.do?lsId=013976#0000"),
        ("범죄수사규칙", "https://www.law.go.kr/LSW//admRulInfoP.do?admRulSeq=2100000272092&chrClsCd=010201#AJAX"),
        ("형사소송법", "https://www.law.go.kr/LSW/lsInfoP.do?lsId=001671&ancYnChk=0#0000"),
        ("수사준칙", "https://www.law.go.kr/LSW/lsLinkProc.do?lsNm=%EA%B2%80%EC%82%AC%EC%99%80+%EC%82%AC%EB%B2%95%EA%B2%BD%EC%B0%B0%EA%B4%80%EC%9D%98+%EC%83%81%ED%98%B8%ED%98%91%EB%A0%A5%EA%B3%BC+%EC%9D%BC%EB%B0%98%EC%A0%81+%EC%88%98%EC%82%AC%EC%A4%80%EC%B9%99%EC%97%90+%EA%B4%80%ED%95%9C+%EA%B7%9C%EC%A0%95&chrClsCd=010202&mode=20&ancYnChk=0#"),
        ("형법", "https://www.law.go.kr/lsSc.do?query=%ED%98%95%EB%B2%95#undefined")
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        for label, url in urls:
            try:
                await page.goto(url, wait_until="networkidle", timeout=15000)
                title = await page.title()
                try:
                    h2 = await page.inner_text("h2", timeout=5000)
                except:
                    h2 = "N/A"
                print(f"Label: {label} | H2: {h2.strip()} | URL: {url}")
            except Exception as e:
                print(f"Error for {label}: {e}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_urls())
