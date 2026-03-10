"""Base class for law.go.kr scrapers sharing common DOM patterns (lsInfoP/admRulInfoP)."""

from __future__ import annotations

import asyncio
import logging
import re
from abc import abstractmethod
from collections.abc import AsyncGenerator
from typing import TypedDict, Optional, cast, Union

from bs4 import BeautifulSoup

from law.config import SELECTORS_LAW
from law.scrapers.base import BaseScraper, SelectorNotFoundError

logger = logging.getLogger(__name__)


class ArticleExtractionResult(TypedDict):
    number: str
    title: str
    content: str
    is_addendum: bool
    addendum_name: Optional[str]

class LawGoKrScraper(BaseScraper):
    """Common logic for law.go.kr statutory/administrative rule scrapers."""

    async def validate_page_loaded(self) -> bool:
        body = SELECTORS_LAW["law_body"]
        alt = SELECTORS_LAW["body_content"]
        el = (await self.page.query_selector(body) or 
              await self.page.query_selector(alt) or 
              await self.page.query_selector("#bodyId") or
              await self.page.query_selector("#conScroll"))
        if el is None:
            raise SelectorNotFoundError(f"{self.name}: law body container not found")
        return True

    async def _wait_for_law_body(self, timeout: int = 30_000) -> None:
        """Wait until main content has actual text content (AJAX loaded)."""
        logger.debug("%s: waiting for law body AJAX content...", self.name)
        deadline = asyncio.get_event_loop().time() + (timeout / 1000)
        while asyncio.get_event_loop().time() < deadline:
            has_content = await self.page.evaluate("""() => {
                const el = document.querySelector('#lsBdy') || 
                           document.querySelector('#bodyContent') || 
                           document.querySelector('#bodyId') || 
                           document.querySelector('.lawcon') || 
                           document.querySelector('#conScroll');
                return el && el.innerText.trim().length > 100;
            }""")
            if has_content:
                return
            await asyncio.sleep(0.5)
        logger.warning("%s: timeout waiting for content, proceeding anyway", self.name)

    async def _extract_structural_articles(self) -> list[ArticleExtractionResult]:
        """Structural Article Extraction via Javascript.
        
        Identifies article blocks, handles addenda (부칙), and merges fragmented text.
        """
        logger.info("%s: performing structural article extraction...", self.name)
        return await self.page.evaluate("""() => {
            const results = [];
            const container = document.querySelector('#lsBdy') || 
                              document.querySelector('#bodyContent') || 
                              document.querySelector('#conScroll') ||
                              document.querySelector('#bodyId');
            if (!container) return [];

            const allElements = Array.from(container.querySelectorAll('div, p'));
            let currentArticle = null;
            let currentAddendum = null;

            for (const el of allElements) {
                const txt = el.innerText.trim();
                if (!txt || txt.length < 2) continue;

                // Detect Addendum header
                if (txt.includes('부 칙')) {
                    const m = txt.match(/부\\s*칙\\s*[<＜]([^>＞]+)[>＞]/);
                    currentAddendum = m ? m[1] : "기본";
                    continue;
                }

                // Match Article Header: "제1조(목적)"
                const headerMatch = txt.match(/^(제\\d+조(?:의\\d+)?)\\s*[\\(（]([^)）]+)[\\)）]/);
                if (headerMatch) {
                    if (currentArticle) results.push(currentArticle);
                    
                    currentArticle = {
                        number: headerMatch[1],
                        title: headerMatch[2],
                        content: txt,
                        is_addendum: !!currentAddendum,
                        addendum_name: currentAddendum
                    };
                } else if (currentArticle) {
                    if (!currentArticle.content.includes(txt)) {
                        currentArticle.content += "\\n" + txt;
                    }
                }
            }
            if (currentArticle) results.push(currentArticle);
            return results;
        }""")

    def _extract_hierarchy_map(self, soup: BeautifulSoup, levels: list[str]) -> dict[str, dict[str, Union[str, None]]]:
        """Common hierarchy extraction logic for sidebar tree.
        
        levels: e.g. ["part", "chapter", "section", "subsection"]
        """
        hierarchy: dict[str, dict] = {}
        current = {lvl: None for lvl in levels}
        
        patterns = {
            "part": r"제\d+편",
            "chapter": r"제\d+장",
            "section": r"제\d+절",
            "subsection": r"제\d+관"
        }

        left = soup.select_one(SELECTORS_LAW["left_tree"])
        if not left:
            return hierarchy

        for item in left.select(SELECTORS_LAW["article_tree_item"]):
            text = item.get_text(strip=True)
            matched_level = None
            
            for lvl in levels:
                if re.match(patterns[lvl], text):
                    matched_level = lvl
                    break
            
            if matched_level:
                current[matched_level] = text
                # Reset lower levels
                reset_idx = levels.index(matched_level) + 1
                for i in range(reset_idx, len(levels)):
                    current[levels[i]] = None
            elif m := re.match(r"(제\d+조(?:의\d+)?)", text):
                hierarchy[m.group(1)] = dict(current)

        return hierarchy
