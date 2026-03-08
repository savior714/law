import asyncio
import json
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_LIST_API_PATH = "https://portal.scourt.go.kr/pgp/pgp1011/selectJdcpctSrchRsltLst.on"
_SOURCE_URL = "https://portal.scourt.go.kr/pgp/index.on?m=PGP1011M01&l=N&c=900"

_FETCH_JS = """
async (apiPath, payload) => {
    try {
        const resp = await fetch(apiPath, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json;charset=UTF-8',
                'Accept': 'application/json, text/plain, */*',
                'sc-pgmid': 'PGP1011M01',
                'submissionid': 'mf_mainFrame_sbm_selectJdcpctSrchLst',
                'Referer': 'https://portal.scourt.go.kr/pgp/index.on?m=PGP1011M01&l=N&c=900',
            },
            body: JSON.stringify(payload),
            credentials: 'include',
        });
        const text = await resp.text();
        return { status: resp.status, text: text };
    } catch (e) {
        return { status: -1, text: e.toString() };
    }
}
"""

async def debug_api():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Using a realistic User-Agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        logger.info(f"Navigating to {_SOURCE_URL}...")
        await page.goto(_SOURCE_URL)
        
        logger.info("Waiting for WebSquare5 JS (15s)...")
        await asyncio.sleep(15)
        
        # Click the '형사' category in the tree to initialize session
        logger.info("Clicking 'Criminal' (형사) category tree label...")
        try:
            # We use a broad selector to find the label containing "형사"
            criminal_label = await page.wait_for_selector("text=형사", timeout=10000)
            if criminal_label:
                await criminal_label.click()
                logger.info("Clicked '형사' label.")
            else:
                logger.warning("'형사' label not found via text.")
        except Exception as e:
            logger.warning(f"Failed to click '형사' label: {e}")
            
        await asyncio.sleep(5)
        
        payload = {
          "dma_searchParam": {
            "srchwd": "형사",
            "sort": "jis_jdcpc_instn_dvs_cd_s asc, $relevance desc, prnjdg_ymd_o desc, jdcpct_gr_cd_s asc",
            "sortType": "정확도",
            "searchRange": "",
            "tpcJdcpctCsAlsYn": "",
            "csNoLstCtt": "",
            "csNmLstCtt": "",
            "prvsRefcCtt": "",
            "searchScope": "",
            "jisJdcpcInstnDvsCd": "",
            "jdcpctCdcsCd": "02",
            "prnjdgYmdFrom": "",
            "prnjdgYmdTo": "",
            "grpJdcpctGrCd": "",
            "cortNm": "",
            "pageNo": "1",
            "jisJdcpcInstnDvsCdGrp": "",
            "grpJdcpctGrCdGrp": "",
            "jdcpctCdcsCdGrp": "",
            "adjdTypCdGrp": "",
            "pageSize": "10",
            "reSrchFlag": "",
            "befSrchwd": "형사",
            "preSrchConditions": "",
            "initYn": "N",
            "totalCount": "0",
            "jdcpctGrCd": "111|112|130|141|180|182|232|235|201",
            "category": "jdcpct",
            "isKwdSearch": "N"
          }
        }
        
        logger.info("Calling API with complete payload after tree click...")
        result = await page.evaluate(_FETCH_JS, [_LIST_API_PATH, payload])
        status = result.get("status")
        text = result.get("text", "")
        
        logger.info(f"Status: {status}")
        if status == 200:
            try:
                data = json.loads(text)
                if "errorMessage" in str(data):
                    logger.error("API returned JSON but with ERROR message.")
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    logger.info("Success! API returned results.")
                    # Print a few items
                    items = data.get("data", {}).get("dlt_jdcpctRslt", [])
                    logger.info(f"Items: {len(items)}")
                    print(json.dumps(items[:2], indent=2, ensure_ascii=False))
            except Exception:
                logger.error("Response is NOT JSON although status 200:")
                print(text[:1000])
        else:
            logger.error(f"Error Status {status}:")
            print(text[:1000])
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_api())
