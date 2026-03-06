"""BaseScraper abstract class defining the Playwright lifecycle."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from law.config import DEFAULT_TIMEOUT_MS, HEADLESS, MAX_RETRIES, NAVIGATION_DELAY_SEC
from law.models.schemas import Attachment

logger = logging.getLogger(__name__)


class SelectorNotFoundError(Exception):
    """Raised when an expected DOM selector is missing from the page."""


class BaseScraper(ABC):
    """Abstract base for all site-specific scrapers.

    Subclasses must implement ``scrape()`` and ``validate_page_loaded()``.
    """

    name: str = ""
    source_url: str = ""

    def __init__(self) -> None:
        self._playwright: Any = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not initialised. Call init_browser() first.")
        return self._page

    # ── Lifecycle ──────────────────────────────────────────────────────

    async def init_browser(self, headless: bool = HEADLESS) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="ko-KR",
        )
        self._page = await self._context.new_page()
        self._page.set_default_timeout(DEFAULT_TIMEOUT_MS)

    async def close(self) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    # ── Navigation helpers ─────────────────────────────────────────────

    async def safe_navigate(self, url: str, wait_selector: str | None = None) -> None:
        """Navigate to *url* with retry logic and optional selector wait."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                await self.page.goto(url, wait_until="domcontentloaded")
                if wait_selector:
                    await self.page.wait_for_selector(wait_selector, timeout=DEFAULT_TIMEOUT_MS)
                await asyncio.sleep(NAVIGATION_DELAY_SEC)
                return
            except Exception:
                delay = 5 * (3 ** (attempt - 1))  # 5s, 15s, 45s
                logger.warning(
                    "%s: navigation attempt %d/%d failed for %s — retrying in %ds",
                    self.name, attempt, MAX_RETRIES, url, delay,
                )
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(delay)

    async def get_page_content(self) -> str:
        """Return the full HTML of the current page."""
        return await self.page.content()

    async def _scrape_attachments(self) -> list[Attachment]:
        """Navigate to [별표/서식] tab and collect PDF/HWP links from law.go.kr pages."""
        results: list[Attachment] = []
        try:
            # Common tab pattern for law.go.kr (Tab 2 is usually annexes)
            # Try both text match and common ID
            tab = await self.page.query_selector("text='별표/서식'") or await self.page.query_selector("#tabSms_2")
            if not tab:
                return []

            await tab.click()
            # Wait for content inside or the specific list container
            try:
                await self.page.wait_for_selector(".ls_sms_list li, #smsBody li", timeout=5000)
            except Exception:
                # If no list items, maybe they are empty
                pass

            items = await self.page.query_selector_all(".ls_sms_list li, #smsBody li")
            for item in items:
                label_el = await item.query_selector("dt") or item
                label = (await label_el.inner_text()).strip().split("\n")[0]

                # PDF icon: class ico_pdf or icon with alt 'pdf'
                pdf_el = await item.query_selector("a.ico_pdf, a[title*='PDF'], a[title*='pdf']")
                hwp_el = await item.query_selector("a.ico_hwp, a[title*='HWP'], a[title*='hwp']")

                pdf_url = await pdf_el.get_attribute("href") if pdf_el else None
                hwp_url = await hwp_el.get_attribute("href") if hwp_el else None

                if pdf_url:
                    # User: "pdf가 우선으로 받고"
                    results.append(Attachment(name=label, pdf_url=pdf_url, has_pdf_priority=True))
                elif hwp_url:
                    # User: "pdf가 없는 경우 hwp를 받지 말고 그냥 로그나 알림을 줬으면 좋겠어"
                    logger.warning("%s: '%s' has NO PDF. Skipping HWP download as requested. (HWP URL available)", self.name, label)
                    results.append(Attachment(name=label, hwp_url=hwp_url, has_pdf_priority=False))

            # Important: Switch back to [본문] tab for article extraction
            main_tab = await self.page.query_selector("text='본문'") or await self.page.query_selector("#tabSms_1")
            if main_tab:
                await main_tab.click()
                await asyncio.sleep(2)
        except Exception:
            logger.debug("%s: error during attachment scraping", self.name, exc_info=True)

        return results

    # ── Abstract interface ─────────────────────────────────────────────

    @abstractmethod
    async def scrape(self) -> AsyncGenerator[Any, None]:
        """Yield validated Pydantic model instances for each scraped record."""
        yield  # pragma: no cover

    @abstractmethod
    async def validate_page_loaded(self) -> bool:
        """Return True if the page contains expected elements, raise otherwise."""
        ...
