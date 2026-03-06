"""Scraper for precedent search on law.go.kr (precSc.do).

Scrapes criminal case precedents with pagination and detail page extraction.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncGenerator
from datetime import date

from bs4 import BeautifulSoup

from law.config import NAVIGATION_DELAY_SEC, SELECTORS_LAW, SOURCES
from law.models.schemas import Precedent
from law.scrapers.base import BaseScraper, SelectorNotFoundError
from law.utils.text import clean_html_text

logger = logging.getLogger(__name__)

SOURCE_KEY = "law_go_kr_precedent"


class LawPrecedentScraper(BaseScraper):
    """Scrapes criminal precedents from law.go.kr precSc.do."""

    def __init__(self) -> None:
        super().__init__()
        src = SOURCES[SOURCE_KEY]
        self.name = SOURCE_KEY
        self.source_url = src["url"]

    # Detail page base URL confirmed via live testing (2026-03-07)
    _DETAIL_BASE = "https://www.law.go.kr/precInfoP.do?mode=0&precSeq={prec_seq}"
    # Keyword that switches results from tax-only defaults to general court (형사) precedents
    _SEARCH_KEYWORD = "형사"

    async def validate_page_loaded(self) -> bool:
        el = await self.page.query_selector("[id^='licPrec']") or await self.page.query_selector("#listDiv")
        if el is None:
            raise SelectorNotFoundError(f"{self.name}: result container not found")
        return True

    async def _setup_search(self) -> None:
        """Navigate to precSc.do and search '형사' to surface court (not tax) precedents."""
        await self.safe_navigate(self.source_url)
        await asyncio.sleep(3)

        # The page default shows 최신 조세판례 (tax cases).
        # Searching "형사" switches results to general court precedents with precView() links.
        try:
            inner_input = await self.page.query_selector("#innerQuery")
            if inner_input:
                await inner_input.fill(self._SEARCH_KEYWORD)
                await inner_input.press("Enter")
                await asyncio.sleep(4)
            else:
                logger.warning("%s: #innerQuery not found — results may be tax-only", self.name)
        except Exception:
            logger.debug("%s: could not interact with #innerQuery", self.name)

        await self.page.wait_for_selector("[id^='licPrec']", timeout=15_000)

    async def scrape(self) -> AsyncGenerator[Precedent, None]:
        await self._setup_search()
        logger.info("%s: search complete, starting extraction", self.name)

        page_num = 1
        scraped = 0

        while True:
            items = await self.page.query_selector_all("[id^='licPrec']")
            if not items:
                break

            for item in items:
                link = await item.query_selector("a")
                if not link:
                    continue

                onclick = await link.get_attribute("onclick") or ""

                # Skip external-site items (showExternalLink → taxlaw, etc.)
                if "showExternalLink" in onclick:
                    continue

                # Extract precSeq from: javascript:precView('615731');return false;
                m = re.search(r"precView\('(\d+)'\)", onclick)
                if not m:
                    continue

                detail_url = self._DETAIL_BASE.format(prec_seq=m.group(1))
                prec = await self._scrape_detail(detail_url)
                if prec:
                    yield prec
                    scraped += 1
                    if scraped % 50 == 0:
                        logger.info("%s: scraped %d", self.name, scraped)

            has_next = await self._go_next_page()
            if not has_next:
                break
            page_num += 1
            await asyncio.sleep(NAVIGATION_DELAY_SEC)
            await self.page.wait_for_selector("[id^='licPrec']", timeout=15_000)

        logger.info("%s: completed — %d precedents scraped", self.name, scraped)

    async def _go_next_page(self) -> bool:
        """Click the next unvisited page number in the AJAX pagination."""
        try:
            # Pagination: <ol><li class='on'>N</li><li><a href='#AJAX'>N+1</a></li>...
            next_link = await self.page.query_selector(".paging ol li:not(.on) a")
            if not next_link:
                return False
            await next_link.click()
            return True
        except Exception:
            return False

    async def _scrape_detail(self, href: str) -> Precedent | None:
        """Open a precInfoP.do detail page and extract data."""
        try:
            url = href if href.startswith("http") else f"https://www.law.go.kr{href}"
            await self.safe_navigate(url)

            html = await self.get_page_content()
            soup = BeautifulSoup(html, "lxml")

            # precInfoP.do uses #bodyContent as the main container
            body = soup.select_one("#bodyContent")
            if body is None:
                return None

            # Case number / name are in the page title area
            case_number = self._extract_text(soup, ".casenm, .subtit1, h2.case_title") or ""
            if not case_number.strip():
                # Fall back to parsing from the page <title>
                title_tag = soup.find("title")
                if title_tag:
                    case_number = title_tag.get_text().split("|")[0].strip()
            if not case_number.strip():
                return None

            case_name = self._extract_text(soup, ".casename, .subtit2")
            court = self._extract_text(soup, ".court, .court_nm") or "대법원"
            decision_date = self._parse_date(self._extract_text(soup, ".decision_date, .date, .jdgmDt"))

            # Extract content sections
            holding = self._extract_section(soup, "판시사항")
            summary = self._extract_section(soup, "판결요지")
            full_text = self._extract_section(soup, "전문") or self._extract_section(soup, "판례내용")
            ref_statutes_text = self._extract_section(soup, "참조조문")
            ref_cases_text = self._extract_section(soup, "참조판례")

            ref_statutes = [s.strip() for s in ref_statutes_text.split(",") if s.strip()] if ref_statutes_text else []
            ref_cases = [s.strip() for s in ref_cases_text.split(",") if s.strip()] if ref_cases_text else []

            return Precedent(
                source_key=SOURCE_KEY,
                case_number=case_number.strip(),
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
            logger.exception("Failed to scrape detail page: %s", href)
            return None

    @staticmethod
    def _extract_text(soup: BeautifulSoup, selector: str) -> str | None:
        el = soup.select_one(selector)
        if el:
            return clean_html_text(el.get_text())
        return None

    @staticmethod
    def _extract_section(soup: BeautifulSoup, section_name: str) -> str | None:
        """Find a section by its heading text and return the content that follows."""
        for heading in soup.find_all(["h3", "h4", "dt", "strong"]):
            if section_name in heading.get_text():
                # Get the next sibling content
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
