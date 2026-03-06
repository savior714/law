"""Scraper for criminal precedents on portal.scourt.go.kr.

The Supreme Court judicial information portal requires careful session handling
and uses heavy JS rendering.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncGenerator
from datetime import date

from bs4 import BeautifulSoup

from law.config import SCOURT_DELAY_SEC, SELECTORS_SCOURT, SOURCES
from law.models.schemas import Precedent
from law.scrapers.base import BaseScraper, SelectorNotFoundError
from law.utils.text import clean_html_text

logger = logging.getLogger(__name__)

SOURCE_KEY = "scourt_criminal_precedent"


class ScourtPrecedentScraper(BaseScraper):
    """Scrapes criminal precedents from the Supreme Court portal."""

    def __init__(self) -> None:
        super().__init__()
        src = SOURCES[SOURCE_KEY]
        self.name = SOURCE_KEY
        self.source_url = src["url"]

    async def validate_page_loaded(self) -> bool:
        # The portal has various containers; check for the search form or result area
        el = (
            await self.page.query_selector(SELECTORS_SCOURT["search_input"])
            or await self.page.query_selector(SELECTORS_SCOURT["result_list"])
            or await self.page.query_selector("#contents")
        )
        if el is None:
            raise SelectorNotFoundError(f"{self.name}: portal page did not load expected elements")
        return True

    async def _handle_initial_load(self) -> None:
        """Handle session initialization, terms acceptance, etc."""
        await self.safe_navigate(self.source_url)

        # Wait for page to settle (heavy JS)
        await asyncio.sleep(3)

        # Accept terms popup if present
        try:
            agree_btn = await self.page.query_selector("#agree_btn, .btn_agree, button:has-text('동의')")
            if agree_btn:
                await agree_btn.click()
                await asyncio.sleep(1)
        except Exception:
            pass  # No popup — continue

    async def _execute_search(self, year: int | None = None) -> None:
        """Execute search, optionally filtered by year."""
        search_input = await self.page.query_selector(SELECTORS_SCOURT["search_input"])
        if search_input:
            await search_input.fill("")

        # Set date range filter if year is specified
        if year:
            try:
                await self.page.evaluate(
                    f"""() => {{
                        const fromDate = document.querySelector('#search_fr_dt, #srchFrDt');
                        const toDate = document.querySelector('#search_to_dt, #srchToDt');
                        if (fromDate) fromDate.value = '{year}-01-01';
                        if (toDate) toDate.value = '{year}-12-31';
                    }}"""
                )
            except Exception:
                logger.debug("Date range filter not available for year %d", year)

        search_btn = await self.page.query_selector(SELECTORS_SCOURT["search_button"])
        if search_btn:
            await search_btn.click()
        await asyncio.sleep(SCOURT_DELAY_SEC)

    async def scrape(self) -> AsyncGenerator[Precedent, None]:
        await self._handle_initial_load()
        await self.validate_page_loaded()

        # Try year-by-year scraping for completeness
        current_year = date.today().year
        scraped_total = 0

        for year in range(current_year, 1999, -1):
            await self._execute_search(year=year)
            count = 0

            while True:
                items = await self.page.query_selector_all(
                    f"{SELECTORS_SCOURT['result_item']}, .tbl_type01 tbody tr"
                )
                if not items:
                    break

                for i in range(len(items)):
                    # Re-query items since page may have changed
                    items = await self.page.query_selector_all(
                        f"{SELECTORS_SCOURT['result_item']}, .tbl_type01 tbody tr"
                    )
                    if i >= len(items):
                        break

                    prec = await self._scrape_item(items[i])
                    if prec:
                        yield prec
                        count += 1

                # Try next page
                has_next = await self._go_next_page()
                if not has_next:
                    break

            scraped_total += count
            if count > 0:
                logger.info("%s: year %d — %d precedents", self.name, year, count)

        logger.info("%s: completed — %d total precedents", self.name, scraped_total)

    async def _scrape_item(self, item_el: object) -> Precedent | None:
        """Click a result item, extract detail, and navigate back."""
        try:
            # Get item text before clicking
            item_text = await item_el.inner_text()

            link = await item_el.query_selector("a")
            if link:
                await link.click()
            else:
                await item_el.click()

            await asyncio.sleep(SCOURT_DELAY_SEC)

            html = await self.get_page_content()
            soup = BeautifulSoup(html, "lxml")

            case_number = self._extract_field(soup, "사건번호") or self._parse_case_number(item_text)
            if not case_number:
                await self.page.go_back()
                await asyncio.sleep(SCOURT_DELAY_SEC)
                return None

            decision_date = self._parse_date(self._extract_field(soup, "선고일자"))
            court = self._extract_field(soup, "법원") or "대법원"
            case_name = self._extract_field(soup, "사건명")

            # Full judgment text
            full_text_el = soup.select_one(".judgment_text, .content_area, #divJudgmentText")
            full_text = clean_html_text(full_text_el.get_text()) if full_text_el else None

            prec = Precedent(
                source_key=SOURCE_KEY,
                case_number=case_number,
                case_name=case_name,
                court=court,
                decision_date=decision_date,
                full_text=full_text,
            )

            await self.page.go_back()
            await asyncio.sleep(SCOURT_DELAY_SEC)
            return prec

        except Exception:
            logger.exception("Failed to scrape item")
            try:
                await self.page.go_back()
                await asyncio.sleep(SCOURT_DELAY_SEC)
            except Exception:
                pass
            return None

    async def _go_next_page(self) -> bool:
        """Try to navigate to the next results page. Returns False if no more pages."""
        try:
            pagination = await self.page.query_selector(SELECTORS_SCOURT["pagination"])
            if not pagination:
                return False

            next_link = await pagination.query_selector("a:has-text('다음'), .next a, a.next")
            if not next_link:
                return False

            is_disabled = await next_link.get_attribute("class") or ""
            if "disabled" in is_disabled:
                return False

            await next_link.click()
            await asyncio.sleep(SCOURT_DELAY_SEC)
            return True
        except Exception:
            return False

    @staticmethod
    def _extract_field(soup: BeautifulSoup, label: str) -> str | None:
        """Find a label (th/dt/strong) and return its adjacent value."""
        for el in soup.find_all(["th", "dt", "strong", "span"]):
            if label in el.get_text():
                sibling = el.find_next_sibling(["td", "dd", "span"])
                if sibling:
                    return clean_html_text(sibling.get_text())
        return None

    @staticmethod
    def _parse_case_number(text: str) -> str | None:
        m = re.search(r"\d{4}\s*[가-힣]+\s*\d+", text)
        return m.group().strip() if m else None

    @staticmethod
    def _parse_date(text: str | None) -> date | None:
        if not text:
            return None
        m = re.search(r"(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})", text)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return None
