"""Scraper for criminal precedents on portal.scourt.go.kr.

The Supreme Court portal uses the WebSquare5 (w2ui) framework, which requires
~15 seconds of JS initialization before any DOM interaction is possible.
All element IDs follow the pattern: mf_mainFrame_<component_id>.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncGenerator
from datetime import date

from bs4 import BeautifulSoup

from law.config import SCOURT_DELAY_SEC, SCOURT_INIT_WAIT_SEC, SELECTORS_SCOURT, SOURCES
from law.models.schemas import Precedent
from law.scrapers.base import BaseScraper, SelectorNotFoundError
from law.utils.text import clean_html_text

logger = logging.getLogger(__name__)

SOURCE_KEY = "scourt_criminal_precedent"


class ScourtPrecedentScraper(BaseScraper):
    """Scrapes criminal precedents from the Supreme Court portal (WebSquare5)."""

    def __init__(self) -> None:
        super().__init__()
        src = SOURCES[SOURCE_KEY]
        self.name = SOURCE_KEY
        self.source_url = src["url"]

    async def validate_page_loaded(self) -> bool:
        el = await self.page.query_selector("#mf_mainFrame")
        if el is None:
            raise SelectorNotFoundError(f"{self.name}: #mf_mainFrame not found — WebSquare5 may not have initialised")
        return True

    async def _handle_initial_load(self) -> None:
        """Navigate and wait for WebSquare5 framework to fully initialise."""
        await self.safe_navigate(self.source_url)
        logger.info("%s: waiting %ds for WebSquare5 initialisation...", self.name, SCOURT_INIT_WAIT_SEC)
        await asyncio.sleep(SCOURT_INIT_WAIT_SEC)

    async def _execute_search(self) -> None:
        """Clear the search box and execute a blank search to list all cases."""
        search_input = await self.page.query_selector(SELECTORS_SCOURT["search_input"])
        if search_input:
            await search_input.click()
            await search_input.fill("")

        search_btn = await self.page.query_selector(SELECTORS_SCOURT["search_button"])
        if search_btn:
            await search_btn.click()
        else:
            # Fallback: press Enter in the search input
            if search_input:
                await search_input.press("Enter")

        await asyncio.sleep(SCOURT_DELAY_SEC * 2)

    async def scrape(self) -> AsyncGenerator[Precedent, None]:
        await self._handle_initial_load()
        await self.validate_page_loaded()
        await self._execute_search()

        scraped_total = 0
        page_num = 1

        while True:
            items = await self.page.query_selector_all(SELECTORS_SCOURT["result_item"])
            if not items:
                logger.info("%s: no items found on page %d — stopping", self.name, page_num)
                break

            for item in items:
                prec = await self._scrape_item(item)
                if prec:
                    yield prec
                    scraped_total += 1

            has_next = await self._go_next_page(page_num)
            if not has_next:
                break
            page_num += 1

        logger.info("%s: completed — %d total precedents", self.name, scraped_total)

    async def _scrape_item(self, item_el: object) -> Precedent | None:
        """Click a result item, extract detail from the detail view, then go back."""
        try:
            list_text = await item_el.inner_text()

            await item_el.click()
            # Wait for detail container to appear - WebSquare5 is slow
            try:
                await self.page.wait_for_selector("#mf_mainFrame_contents, [id*='detail_view'], .detailCon", timeout=10000)
            except Exception:
                logger.warning("%s: timeout waiting for detail view for item", self.name)
            
            await asyncio.sleep(SCOURT_DELAY_SEC)

            html = await self.get_page_content()
            soup = BeautifulSoup(html, "lxml")

            # Detail content loads inside the mainFrame — probe common containers
            # Usually .viewCon or #mf_mainFrame_contents
            detail_el = (
                soup.select_one(".viewCon") 
                or soup.select_one("#mf_mainFrame_contents")
                or soup.select_one("#mf_mainFrame")
            )
            
            # If we still failed to get clean detail, take the whole frame body
            full_text_raw = (detail_el.get_text("\n") if detail_el else list_text).strip()

            case_number = self._parse_case_number(full_text_raw) or self._parse_case_number(list_text)
            if not case_number:
                logger.warning("%s: could not find case number in detail", self.name)
                # Try to go back anyway
                await self.page.go_back()
                await asyncio.sleep(SCOURT_DELAY_SEC * 2)
                return None

            decision_date = self._parse_date_from_text(full_text_raw)
            case_name = self._extract_label(full_text_raw, "사건명") or self._extract_label(list_text, "사건명")
            court = self._extract_label(full_text_raw, "법원") or "대법원"
            full_text = clean_html_text(full_text_raw)

            # Navigate back to results list
            # Usually SCourt detail has a 'List' button, but go_back is safer if it reloads properly
            await self.page.go_back()
            await asyncio.sleep(SCOURT_DELAY_SEC * 3) # Wait longer for list refresh
            return Precedent(
                source_key=SOURCE_KEY,
                case_number=case_number,
                case_name=case_name,
                court=court,
                decision_date=decision_date,
                full_text=full_text,
            )

        except Exception:
            logger.exception("%s: failed to scrape item", self.name)
            try:
                await self.page.go_back()
                await asyncio.sleep(SCOURT_DELAY_SEC)
            except Exception:
                pass
            return None

    async def _go_next_page(self, current_page: int) -> bool:
        """Attempt to navigate to the next page via WebSquare5 pagination."""
        try:
            # WebSquare5 pagination buttons follow pattern: mf_mainFrame_*pageNo* or similar
            next_page = current_page + 1
            # Try direct page number element click
            next_el = await self.page.query_selector(
                f"[id*='pageNo'][id*='{next_page}'], [id*='paging'][id*='{next_page}']"
            )
            if next_el:
                await next_el.click()
                await asyncio.sleep(SCOURT_DELAY_SEC)
                return True

            # Try generic next button
            next_btn = await self.page.query_selector(
                "[id*='btnNext'], [id*='btn_next'], [id*='nextPage'], [class*='btnNext']"
            )
            if next_btn:
                is_disabled = await next_btn.get_attribute("class") or ""
                if "disabled" in is_disabled or "inactive" in is_disabled:
                    return False
                await next_btn.click()
                await asyncio.sleep(SCOURT_DELAY_SEC)
                return True

            return False
        except Exception:
            return False

    @staticmethod
    def _parse_case_number(text: str) -> str | None:
        m = re.search(r"\d{4}\s*[가-힣]+\s*\d+", text)
        return m.group().strip() if m else None

    @staticmethod
    def _parse_date_from_text(text: str) -> date | None:
        m = re.search(r"(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})", text)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return None
        return None

    @staticmethod
    def _extract_label(text: str, label: str) -> str | None:
        m = re.search(rf"{label}\s*[:\uff1a]?\s*(.+)", text)
        return m.group(1).strip()[:100] if m else None
