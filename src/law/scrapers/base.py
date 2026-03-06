"""BaseScraper abstract class defining the Playwright lifecycle."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from law.config import DEFAULT_TIMEOUT_MS, HEADLESS, MAX_RETRIES, NAVIGATION_DELAY_SEC

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

    # ── Abstract interface ─────────────────────────────────────────────

    @abstractmethod
    async def scrape(self) -> AsyncGenerator[Any, None]:
        """Yield validated Pydantic model instances for each scraped record."""
        yield  # pragma: no cover

    @abstractmethod
    async def validate_page_loaded(self) -> bool:
        """Return True if the page contains expected elements, raise otherwise."""
        ...
