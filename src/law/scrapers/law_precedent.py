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

    async def validate_page_loaded(self) -> bool:
        el = await self.page.query_selector("#precSrchResult") or await self.page.query_selector(".srch_list")
        if el is None:
            raise SelectorNotFoundError(f"{self.name}: search result container not found")
        return True

    async def _setup_search(self) -> int:
        """Navigate, set filters for criminal cases, execute search. Returns total result count."""
        await self.safe_navigate(self.source_url)

        # Open advanced search and set criminal case filter
        try:
            await self.page.click("#lbBtnSrch")  # 상세검색
            await asyncio.sleep(0.5)
        except Exception:
            logger.debug("Advanced search panel may already be open")

        # Set case type to 형사
        try:
            await self.page.select_option("#precKindSel", label="형사")
        except Exception:
            logger.warning("Could not set case type filter via select. Trying alternative approach.")
            try:
                await self.page.evaluate("document.querySelector('#precKindSel').value = '형사'")
            except Exception:
                logger.warning("Case type filter not available — proceeding without filter")

        # Execute search
        await self.page.click("#btnSearch")
        await self.page.wait_for_selector(".srch_list", timeout=15_000)

        # Parse total count
        total_el = await self.page.query_selector(SELECTORS_LAW["total_count"])
        if total_el:
            total_text = await total_el.inner_text()
            m = re.search(r"[\d,]+", total_text)
            if m:
                return int(m.group().replace(",", ""))
        return 0

    async def scrape(self) -> AsyncGenerator[Precedent, None]:
        total = await self._setup_search()
        logger.info("%s: found %d total results", self.name, total)

        page_num = 1
        scraped = 0

        while True:
            # Get all result links on current page
            items = await self.page.query_selector_all(".srch_list .list_item a, .srch_list li a")
            if not items:
                break

            hrefs: list[str] = []
            for item in items:
                href = await item.get_attribute("href")
                if href:
                    hrefs.append(href)

            for href in hrefs:
                prec = await self._scrape_detail(href)
                if prec:
                    yield prec
                    scraped += 1
                    if scraped % 50 == 0:
                        logger.info("%s: scraped %d / %d", self.name, scraped, total)

            # Try next page
            next_btn = await self.page.query_selector(SELECTORS_LAW["pagination_next"])
            if not next_btn:
                break

            is_disabled = await next_btn.get_attribute("class") or ""
            if "disabled" in is_disabled:
                break

            page_num += 1
            await next_btn.click()
            await asyncio.sleep(NAVIGATION_DELAY_SEC)
            await self.page.wait_for_selector(".srch_list", timeout=15_000)

        logger.info("%s: completed — %d precedents scraped", self.name, scraped)

    async def _scrape_detail(self, href: str) -> Precedent | None:
        """Open a precedent detail page and extract data."""
        try:
            url = href if href.startswith("http") else f"https://www.law.go.kr{href}"
            await self.safe_navigate(url)

            html = await self.get_page_content()
            soup = BeautifulSoup(html, "lxml")

            # Extract case metadata
            case_number = self._extract_text(soup, ".subtit1, .casenm, h2") or ""
            if not case_number.strip():
                return None

            case_name = self._extract_text(soup, ".subtit2, .casename")
            court = self._extract_text(soup, ".court") or "대법원"
            decision_date = self._parse_date(self._extract_text(soup, ".decision_date, .date"))

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
