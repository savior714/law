"""Base class for many legal decision types on law.go.kr.
Includes precedents, constitutional decisions, legal interpretations, and admin appeals.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncGenerator
from datetime import date

from bs4 import BeautifulSoup

from law.config import NAVIGATION_DELAY_SEC, SOURCES
from law.models.schemas import Precedent
from law.scrapers.base import BaseScraper, ScrapedItem, SelectorNotFoundError
from law.utils.text import clean_html_text

logger = logging.getLogger(__name__)


class LawGoKrDecisionBaseScraper(BaseScraper):
    """Base scraper for AJAX-based legal decision lists on law.go.kr."""

    def __init__(self, source_key: str) -> None:
        super().__init__()
        src = SOURCES[source_key]
        self.name = source_key
        self.source_url = src.url
        
        # Configuration for specific decision type
        self._list_item_selector = "[id^='lic']"  # Default for prec/detc
        self._detail_url_pattern = r"precView\('(\d+)'\)" # Overridden by subclasses
        self._detail_base_url = "" # Overridden by subclasses

    async def validate_page_loaded(self) -> bool:
        el = await self.page.query_selector(self._list_item_selector) or await self.page.query_selector("#listDiv")
        if el is None:
            raise SelectorNotFoundError(f"{self.name}: result container not found")
        return True

    async def _setup_search(self) -> None:
        """Navigate and perform initial search if needed."""
        await self.safe_navigate(self.source_url)
        await asyncio.sleep(3)
        # Subclasses can add specific search keywords (e.g. '형사')

    async def scrape(self) -> AsyncGenerator[ScrapedItem, None]:
        await self._setup_search()
        logger.info("%s: search complete, starting extraction", self.name)

        scraped = 0
        current_idx = 0
        resume_idx = int(self.resume_checkpoint) if self.resume_checkpoint and self.resume_checkpoint.isdigit() else -1

        while True:
            # Collect all sequence IDs on the current page first
            items = await self.page.query_selector_all(self._list_item_selector)
            if not items:
                break

            seq_ids = []
            for item in items:
                link = await item.query_selector("a")
                if not link:
                    continue
                onclick = await link.get_attribute("onclick") or ""
                m = re.search(self._detail_url_pattern, onclick)
                if m:
                    seq_ids.append(m.group(1))

            for seq in seq_ids:
                if current_idx <= resume_idx:
                    current_idx += 1
                    continue

                detail_url = self._detail_base_url.format(seq=seq)
                decision = await self._scrape_detail(detail_url)
                if decision:
                    # RAG 품질 향상을 위해 관련 키워드가 포함된 경우만 수집
                    # (사건명, 판시사항, 판결요지, 전문 중 하나라도 포함되면 수집)
                    content_to_check = f"{decision.case_name or ''} {decision.holding or ''} {decision.summary or ''} {decision.full_text or ''}"
                    if self.is_relevant(content_to_check):
                        yield decision
                        scraped += 1
                        if scraped % 20 == 0:
                            logger.info("%s: scraped %d (total idx: %d)", self.name, scraped, current_idx)
                    else:
                        logger.debug("%s: skip irrelevant case: %s", self.name, decision.case_number)

                current_idx += 1

            has_next = await self._go_next_page()
            if not has_next:
                break
            
            await asyncio.sleep(NAVIGATION_DELAY_SEC)
            await self.page.wait_for_selector(self._list_item_selector, state="attached", timeout=15_000)

        logger.info("%s: completed — %d records scraped", self.name, scraped)

    async def _go_next_page(self) -> bool:
        """Click the next unvisited page number in the AJAX pagination using JS."""
        try:
            clicked = await self.page.evaluate("""() => {
                const currentLi = document.querySelector(".paging ol li.on");
                if (currentLi && currentLi.nextElementSibling) {
                    const a = currentLi.nextElementSibling.querySelector("a");
                    if (a) {
                        a.click();
                        return true;
                    }
                }
                const nextGrp = document.querySelector(".paging a img[alt*='다음']");
                if (nextGrp && nextGrp.parentElement) {
                    nextGrp.parentElement.click();
                    return true;
                }
                return false;
            }""")
            return clicked
        except Exception:
            return False

    async def _scrape_detail(self, url: str) -> Precedent | None:
        """Scrape detail page using a new page/tab to keep the list page alive."""
        detail_page = None
        try:
            detail_page = await self.context.new_page()
            await detail_page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            
            html = await detail_page.content()
            soup = BeautifulSoup(html, "lxml")

            # Check if content exists
            body = soup.select_one("#bodyContent")
            if body is None:
                return None

            # Common fields
            case_number = self._extract_title_info(soup)
            if not case_number:
                return None

            case_name = self._extract_text(soup, ".casename, .subtit2")
            court = self._extract_text(soup, ".court, .court_nm")
            decision_date = self._parse_date(self._extract_text(soup, ".decision_date, .date, .jdgmDt"))
            
            holding = self._extract_section(soup, ["판시사항", "결정", "주문"])
            summary = self._extract_section(soup, ["판결요지", "결정요지", "질의요지"])
            full_text = self._extract_section(soup, ["전문", "판례내용", "회신내용", "재결내용"])
            
            ref_statutes_text = self._extract_section(soup, ["참조조문", "관련법령", "관계법령"])
            ref_cases_text = self._extract_section(soup, ["참조판례", "참조결정례"])

            ref_statutes = [s.strip() for s in ref_statutes_text.split(",") if s.strip()] if ref_statutes_text else []
            ref_cases = [s.strip() for s in ref_cases_text.split(",") if s.strip()] if ref_cases_text else []

            return Precedent(
                source_key=self.name,
                case_number=case_number,
                case_name=case_name,
                court=court,
                decision_date=decision_date,
                holding=holding,
                summary=summary,
                full_text=full_text,
                referenced_statutes=ref_statutes,
                referenced_cases=ref_cases,
            )
        except Exception:
            logger.exception("%s: Failed to scrape detail page: %s", self.name, url)
            return None
        finally:
            if detail_page:
                await detail_page.close()

    def _extract_title_info(self, soup: BeautifulSoup) -> str | None:
        """Extract case number from title area or <title> tag."""
        case_number = self._extract_text(soup, ".casenm, .subtit1, h2.case_title")
        if not case_number:
            title_tag = soup.find("title")
            if title_tag:
                case_number = title_tag.get_text().split("|")[0].strip()
        return case_number.strip() if case_number else None

    @staticmethod
    def _extract_text(soup: BeautifulSoup, selector: str) -> str | None:
        el = soup.select_one(selector)
        if el:
            return clean_html_text(el.get_text())
        return None

    @staticmethod
    def _extract_section(soup: BeautifulSoup, section_names: list[str]) -> str | None:
        """Find a section by any of its heading names and return the content that follows."""
        for heading in soup.find_all(["h3", "h4", "dt", "strong", "p"]):
            text = heading.get_text().strip()
            if any(name in text for name in section_names):
                content_el = heading.find_next_sibling()
                if content_el:
                    return clean_html_text(content_el.get_text())
        return None

    @staticmethod
    def _parse_date(text: str | None) -> date | None:
        if not text:
            return None
        m = re.search(r"(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})", text)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return None
