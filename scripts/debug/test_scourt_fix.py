import asyncio
import sys
import os
from law.scrapers.scourt_precedent import ScourtPrecedentScraper

async def test_single_extraction(srno):
    print(f'Starting test for SRNO: {srno}')
    print(f'CWD: {os.getcwd()}')
    scraper = ScourtPrecedentScraper()
    
    print('Initializing browser...')
    await scraper.init_browser(headless=False)
    
    try:
        # 60s timeout for the whole process
        async with asyncio.timeout(60):
            print('Starting initial load...')
            # Let s handle initial load handle its own internal logs
            await scraper._handle_initial_load()
            
            print(f'Building precedent for SRNO: {srno}')
            dummy_text = "대법원 2026.01.01 선고 2025도1234 판결"
            prec = await scraper._build_precedent(srno, dummy_text)
            
            if prec:
                print('--- Extraction Success ---')
                print(f'Case Number: {prec.case_number}')
                print(f'Full Text Length: {len(prec.full_text) if prec.full_text else 0}')
                print(f'Summary Length: {len(prec.summary) if prec.summary else 0}')
                if prec.full_text and len(prec.full_text) > 0:
                     print(f'Preview: {prec.full_text[:100]}...')
                else:
                     print('NO FULL TEXT EXTRACTED')
            else:
                print('Failed to build precedent (prec is None).')

    except asyncio.TimeoutError:
        print('GLOBAL TIMEOUT (60s) reached.')
    except Exception as e:
        print(f'Crashed with: {e}')
    finally:
        print('Closing browser...')
        await scraper.close()
        print('Done.')

if __name__ == '__main__':
    asyncio.run(test_single_extraction('3315449'))