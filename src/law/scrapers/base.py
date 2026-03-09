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
        self.resume_checkpoint: str | None = None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not initialised. Call init_browser() first.")
        return self._page

    @property
    def context(self) -> BrowserContext:
        if self._context is None:
            raise RuntimeError("Browser context not initialised. Call init_browser() first.")
        return self._context

    @property
    def browser(self) -> Browser:
        if self._browser is None:
            raise RuntimeError("Browser not initialised. Call init_browser() first.")
        return self._browser

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
                # Use domcontentloaded for faster/more reliable loading on law.go.kr
                await self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                if wait_selector:
                    await self.page.wait_for_selector(wait_selector, timeout=DEFAULT_TIMEOUT_MS)
                await asyncio.sleep(NAVIGATION_DELAY_SEC)
                return
            except Exception as e:
                delay = 5 * (3 ** (attempt - 1))
                logger.warning(
                    "%s: navigation attempt %d/%d failed for %s (%s) — retrying in %ds",
                    self.name, attempt, MAX_RETRIES, url, str(e), delay,
                )
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(delay)

    async def get_page_content(self) -> str:
        """Return the full HTML of the current page."""
        return await self.page.content()

    async def ensure_tab_active(self, tab_text: str) -> bool:
        """Ensure a specific tab (본문, 별표/서식 etc) is active."""
        tabs = await self.page.query_selector_all(".tabs a, .ls_tab a, #tab_menu a")
        for t in tabs:
            txt = await t.inner_text()
            if tab_text in txt:
                await t.click()
                await asyncio.sleep(2)
                return True
        return False

    async def _scrape_attachments(self) -> list[Attachment]:
        """Navigate to [별표/서식] tab and collect PDF/HWP links from law.go.kr pages."""
        results: list[Attachment] = []
        try:
            if self.page.is_closed():
                return []

            # 1. '별표/서식' 탭 찾기
            tab = await self.page.query_selector("a:has-text('별표'), a:has-text('첨부'), #bylView, #tabSms_2")
            if not tab:
                logger.debug("%s: attachments tab not found", self.name)
                return []

            await tab.click()
            
            # 2. AJAX 콘텐츠 로딩 대기
            try:
                # Wait for any list items in common attachment containers
                await self.page.wait_for_selector(
                    ".ls_sms_list li, .pconfile li, #smsBody li", 
                    timeout=5000
                )
            except Exception:
                await asyncio.sleep(2)

            if self.page.is_closed(): return results

            # 3. 항목 추출
            extracted_items = await self.page.evaluate("""() => {
                const results = [];
                const selector = '.ls_sms_list li, .pconfile li, #smsBody li, #liBgcolorSpanBy li';
                const items = Array.from(document.querySelectorAll(selector));
                for (const item of items) {
                    const labelEl = item.querySelector("dt, a.blu, b") || item;
                    let label = (labelEl.innerText || "").trim().split('\\n')[0].trim();
                    if (!label || label.includes("주소")) continue;

                    let pdf_url = null, hwpx_url = null, hwp_url = null;
                    const links = item.querySelectorAll("a");
                    for (const a of links) {
                        const href = a.href || "";
                        const txt = (a.innerText || "").toUpperCase();
                        const title = (a.title || "").toUpperCase();
                        
                        if (!pdf_url && (txt.includes("PDF") || title.includes("PDF") || href.includes(".pdf"))) {
                            pdf_url = a.getAttribute("href");
                        }
                        if (!hwpx_url && (txt.includes("HWPX") || title.includes("HWPX") || href.includes("hwpx"))) {
                            hwpx_url = a.getAttribute("href");
                        }
                        if (!hwp_url && (txt.includes("HWP") || title.includes("HWP") || href.includes(".hwp"))) {
                            hwp_url = a.getAttribute("href");
                        }
                    }
                    if (pdf_url || hwpx_url || hwp_url) {
                        results.push({ label, pdf_url, hwpx_url, hwp_url });
                    }
                }
                return results;
            }""")

            for data in extracted_items:
                results.append(Attachment(
                    name=data["label"], 
                    pdf_url=data["pdf_url"], 
                    hwpx_url=data["hwpx_url"],
                    hwp_url=data["hwp_url"],
                    has_pdf_priority=bool(data["pdf_url"])
                ))

            # 4. [본문] 탭으로 복귀 및 로딩 확인
            main_tab = await self.page.query_selector("a:has-text('본문'), #bdyBtnKO, #tabSms_1")
            if main_tab:
                await main_tab.click()
                # Wait for main content to reappear
                try:
                    await self.page.wait_for_selector("#lsBdy, #bodyContent, .lawcon", timeout=7000)
                except:
                    await asyncio.sleep(2)
            else:
                await self.safe_navigate(self.source_url)
                
        except Exception as e:
            logger.debug("%s: error during attachment scraping: %s", self.name, e)
            try:
                if not self.page.is_closed():
                    await self.safe_navigate(self.source_url)
            except: pass

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
