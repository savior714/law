"""Specific scrapers for various legal decision types on law.go.kr."""

from __future__ import annotations

import asyncio
import logging
from law.scrapers.law_go_kr_decision_base import LawGoKrDecisionBaseScraper

logger = logging.getLogger(__name__)


class LawGoKrPrecedentScraper(LawGoKrDecisionBaseScraper):
    """Scraper for court precedents on law.go.kr."""
    
    def __init__(self, source_key: str = "law_go_kr_precedent") -> None:
        super().__init__(source_key)
        self._list_item_selector = "[id^='licPrec']"
        self._detail_url_pattern = r"precView\('(\d+)'\)"
        self._detail_base_url = "https://www.law.go.kr/precInfoP.do?mode=0&precSeq={seq}"

    async def _setup_search(self) -> None:
        """Search '형사' to avoid tax-only default results."""
        await self.safe_navigate(self.source_url)
        await asyncio.sleep(3)
        try:
            inner_input = await self.page.query_selector("#innerQuery")
            if inner_input:
                await inner_input.fill("형사")
                await inner_input.press("Enter")
                await asyncio.sleep(4)
        except Exception:
            logger.debug("%s: could not perform keyword search", self.name)
        await self.page.wait_for_selector(self._list_item_selector, state="attached", timeout=15_000)


class ConstitutionalScraper(LawGoKrDecisionBaseScraper):
    """Scraper for Constitutional Court decisions on law.go.kr."""
    
    def __init__(self, source_key: str = "law_go_kr_constitutional") -> None:
        super().__init__(source_key)
        self._list_item_selector = "[id^='licDetc']"
        self._detail_url_pattern = r"detcView\('(\d+)'\)"
        self._detail_base_url = "https://www.law.go.kr/detcInfoP.do?mode=0&detcSeq={seq}"


class InterpretationScraper(LawGoKrDecisionBaseScraper):
    """Scraper for legal interpretations by MoLEG on law.go.kr."""
    
    def __init__(self, source_key: str = "law_go_kr_interpretation") -> None:
        super().__init__(source_key)
        self._list_item_selector = "[id^='licExpc']"
        self._detail_url_pattern = r"expcView\('(\d+)'\)"
        self._detail_base_url = "https://www.law.go.kr/expcInfoP.do?mode=0&expcSeq={seq}"


class AdminAppealScraper(LawGoKrDecisionBaseScraper):
    """Scraper for administrative appeal decisions on law.go.kr."""
    
    def __init__(self, source_key: str = "law_go_kr_admin_appeal") -> None:
        super().__init__(source_key)
        self._list_item_selector = "[id^='licAllDecc']"
        self._detail_url_pattern = r"allDeccView\('(\d+)'\)"
        # Note: Administrative appeal URLs can sometimes use different seq params, 
        # but allDeccSeq is common on law.go.kr
        self._detail_base_url = "https://www.law.go.kr/allDeccInfoP.do?mode=0&allDeccSeq={seq}"
