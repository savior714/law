import asyncio
import logging
from law.scrapers.law_statute import StatuteScraper

async def test_pdf_extraction():
    # 경찰관직무집행법으로 테스트
    scraper = StatuteScraper("police_duties_act")
    
    # 결과를 파일로 저장
    with open("data/debug_pdf.log", "w", encoding="utf-8") as f:
        f.write("브라우저 초기화 중...\n")
        await scraper.init_browser(headless=True)
        
        try:
            f.write(f"URL 접속: {scraper.source_url}\n")
            await scraper.page.goto(scraper.source_url, wait_until="networkidle")
            await asyncio.sleep(7) 
            
            # 스크린샷 촬영
            await scraper.page.screenshot(path="data/screenshot.png", full_page=False)
            f.write("스크린샷 저장 완료: data/screenshot.png\n")
            
            # 별표/서식 탭 존재 여부 확인
            f.write("\n[탭 검색 및 클릭 시도]\n")
            
            # JS를 통해 "별표"가 포함된 모든 요소를 찾아 상세 정보 기록
            page_analysis = await scraper.page.evaluate("""() => {
                const results = [];
                const all = document.querySelectorAll('a, button, span');
                for (const el of all) {
                    const txt = el.innerText.trim();
                    if (txt.includes('별표')) {
                        results.push({
                            text: txt,
                            tag: el.tagName,
                            id: el.id,
                            className: el.className,
                            isVisible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)
                        });
                    }
                }
                return results;
            }""")
            
            f.write(f"별표 관련 요소 분석 결과: {page_analysis}\n")

            # 클릭 시도
            tab_found = False
            for selector in ["text='별표·서식'", "text='별표/서식'", "text='별표'", "#tabSms_2"]:
                try:
                    tab = await scraper.page.query_selector(selector)
                    if tab and await tab.is_visible():
                        f.write(f"탭 발견 및 클릭 시도: {selector}\n")
                        await tab.click()
                        tab_found = True
                        break
                except: continue
            
            if tab_found:
                await asyncio.sleep(5)
                f.write("탭 클릭 후 5초 대기 완료.\n")
                
                # 텍스트 기반 검색 (PDF, HWP)
                text_search = await scraper.page.evaluate("""() => {
                    const results = [];
                    const all = document.querySelectorAll('a, span, b, font');
                    for (const el of all) {
                        const txt = el.innerText.toUpperCase();
                        if (txt.includes('PDF') || txt.includes('HWP')) {
                            results.push({
                                text: el.innerText.trim(),
                                tag: el.tagName,
                                parentTag: el.parentElement.tagName,
                                className: el.className
                            });
                        }
                    }
                    return results;
                }""")
                f.write(f"PDF/HWP 텍스트 검색 결과: {text_search}\n")

                # 현재 전체 HTML 저장하여 분석
                content = await scraper.page.content()
                with open("data/debug_html.txt", "w", encoding="utf-8") as html_f:
                    html_f.write(content)
                f.write("현재 페이지 HTML을 data/debug_html.txt에 저장했습니다.\n")
            else:
                f.write("탭 클릭 실패.\n")

            f.write("\n별표/서식(PDF) 추출 테스트 시작 (BaseScraper._scrape_attachments 호출)...\n")
            attachments = await scraper._scrape_attachments()
            
            f.write(f"\n최종 추출된 첨부파일 개수: {len(attachments)}\n")
            for i, att in enumerate(attachments):
                status = "PDF 있음" if att.pdf_url else "PDF 없음"
                f.write(f"[{i+1}] {att.name}\n")
                f.write(f"    - 상태: {status}\n")
                if att.pdf_url: f.write(f"    - PDF URL: {att.pdf_url[:100]}...\n")
                if att.hwp_url: f.write(f"    - HWP URL: {att.hwp_url[:100]}...\n")
                f.write(f"    - PDF 우선순위: {att.has_pdf_priority}\n")
                
        except Exception as e:
            f.write(f"\n에러 발생: {str(e)}\n")
        finally:
            await scraper.close()
            f.write("\n작업 완료.")

if __name__ == "__main__":
    asyncio.run(test_pdf_extraction())
