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
            if self.page.is_closed():
                logger.error("%s: browser page is closed before attachment scraping", self.name)
                return []

            # 1. '별표/서식' 탭 찾기 및 클릭
            # 행정규칙 특유의 fSelectJoListTree 패턴이나 ID를 우선 탐색
            tab = (
                await self.page.query_selector("a[onclick*='liBgcolorSpanBy']") or
                await self.page.query_selector("#bylView") or 
                await self.page.query_selector("text='별표·서식'") or 
                await self.page.query_selector("text='별표/서식'") or 
                await self.page.query_selector("text='첨부파일'") or
                await self.page.query_selector("#tabSms_2") or
                await self.page.query_selector("#attFlListView")
            )
            
            if not tab:
                # 텍스트 기반 부분 일치 대체 탐색
                tab = await self.page.query_selector("a:has-text('별표'), button:has-text('별표')")
                
            if not tab:
                logger.debug("%s: attachments tab not found", self.name)
                return []

            await tab.click()
            
            # 2. AJAX 콘텐츠 로딩 대기
            # 행정규칙(.pconfile) 및 일반 법령(.ls_sms_list) 컨테이너 대기
            try:
                await self.page.wait_for_selector(
                    ".ls_sms_list > li, #smsBody > li, .pconfile > li, .pconfile li, #liBgcolorSpanBy li", 
                    timeout=5000
                )
            except Exception:
                await asyncio.sleep(2)

            if self.page.is_closed(): return results

            # 3. 항목 추출
            items = await self.page.query_selector_all(
                ".ls_sms_list > li, #smsBody > li, .pconfile > li, #liBgcolorSpanBy li"
            )
            if not items:
                items = await self.page.query_selector_all(".ls_sms_list li, #smsBody li, .pconfile li")

            for item in items:
                if self.page.is_closed(): break
                # 레이블 추출: 링크 텍스트나 볼드체 우선
                label_el = await item.query_selector("dt, a.blu, a[onclick*='bylInfo'], b") or item
                label = (await label_el.inner_text()).strip()
                label = " ".join(label.split()).split("\n")[0].strip()
                
                if not label or "주소를 복사" in label:
                    continue

                # PDF 아이콘/텍스트 식별
                pdf_el = (
                    await item.query_selector("a.ico_pdf, a[title*='PDF'], a[title*='pdf']") or 
                    await item.query_selector("a:has(img[alt*='PDF']), a:has(img[alt*='pdf'])") or 
                    await item.query_selector("a:has-text('.pdf')")
                )
                
                # HWPX 식별
                hwpx_el = (
                    await item.query_selector("a.ico_hwpx, a[title*='HWPX'], a[title*='hwpx']") or
                    await item.query_selector("a[href*='flExt=hwpx']")
                )

                # HWP 아이콘/텍스트 식별
                hwp_el = (
                    await item.query_selector("a.ico_hwp, a[title*='HWP'], a[title*='hwp']") or 
                    await item.query_selector("a:has(img[alt*='HWP']), a:has(img[alt*='hwp']), a:has(img[alt*='한글'])") or 
                    await item.query_selector("a:has-text('.hwp')")
                )

                pdf_url = await pdf_el.get_attribute("href") if pdf_el else None
                hwpx_url = await hwpx_el.get_attribute("href") if hwpx_el else None
                hwp_url = await hwp_el.get_attribute("href") if hwp_el else None

                if pdf_url or hwpx_url or hwp_url:
                    if pdf_url:
                        results.append(Attachment(
                            name=label, 
                            pdf_url=pdf_url, 
                            hwpx_url=hwpx_url,
                            hwp_url=hwp_url,
                            has_pdf_priority=True
                        ))
                    else:
                        logger.warning(
                            "%s: '%s' has NO PDF. (Available: HWPX=%s, HWP=%s)", 
                            self.name, label, bool(hwpx_url), bool(hwp_url)
                        )
                        results.append(Attachment(
                            name=label, 
                            hwpx_url=hwpx_url,
                            hwp_url=hwp_url, 
                            has_pdf_priority=False
                        ))

            # 4. [본문] 탭으로 복귀 (조문 추출을 위해 필수)
            if not self.page.is_closed():
                main_tab = (
                    await self.page.query_selector("#bdyBtnKO") or
                    await self.page.query_selector("text='본문'") or 
                    await self.page.query_selector("text='행정규칙본문'") or
                    await self.page.query_selector("#tabSms_1") or 
                    await self.page.query_selector("#lsBdyView")
                )
                if main_tab:
                    await main_tab.click()
                    await asyncio.sleep(2)
                else:
                    logger.warning("%s: main tab not found, re-navigating to source URL", self.name)
                    await self.safe_navigate(self.source_url)
        except Exception:
            logger.debug("%s: error during attachment scraping", self.name, exc_info=True)
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
