"""Scraper for statutes on law.go.kr (형법, 형사소송법, 경찰관직무집행법).

All three share the lsInfoP.do page template.
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator

from bs4 import BeautifulSoup

from law.config import SELECTORS_LAW, SOURCES
from law.models.schemas import StatuteArticle
from law.scrapers.base import BaseScraper, SelectorNotFoundError
from law.utils.text import clean_html_text

logger = logging.getLogger(__name__)


class StatuteScraper(BaseScraper):
    """Scrapes statute articles from law.go.kr lsInfoP.do pages."""

    def __init__(self, source_key: str) -> None:
        super().__init__()
        src = SOURCES[source_key]
        self.name = source_key
        self.source_url = src["url"]
        self._law_name = src["name"]
        self._source_key = source_key

    async def validate_page_loaded(self) -> bool:
        body = SELECTORS_LAW["law_body"]
        alt = SELECTORS_LAW["body_content"]
        el = await self.page.query_selector(body) or await self.page.query_selector(alt)
        if el is None:
            raise SelectorNotFoundError(f"{self.name}: neither {body} nor {alt} found")
        return True

    async def _navigate_to_statute(self) -> None:
        """Navigate to the statute page, handling search-based access for 형법."""
        if self._source_key == "criminal_act":
            await self.safe_navigate(self.source_url)
            # Click the first search result that matches "형법" (the statute, not special laws)
            await self.page.wait_for_selector("#dtlBtn1", timeout=10_000)
            await self.page.click("#dtlBtn1")
            await self.page.wait_for_selector(SELECTORS_LAW["law_body"], timeout=15_000)
        else:
            await self.safe_navigate(self.source_url, wait_selector=SELECTORS_LAW["law_body"])

    async def scrape(self) -> AsyncGenerator[StatuteArticle, None]:
        await self._navigate_to_statute()
        await self.validate_page_loaded()

        html = await self.get_page_content()
        soup = BeautifulSoup(html, "lxml")

        # Parse hierarchy from left sidebar tree
        hierarchy = self._parse_hierarchy(soup)

        # Parse articles from law body
        body_el = soup.select_one(SELECTORS_LAW["law_body"]) or soup.select_one(SELECTORS_LAW["body_content"])
        if body_el is None:
            return

        articles = self._extract_articles(body_el, hierarchy)

        for article in articles:
            yield article

        logger.info("%s: extracted %d articles", self.name, len(articles))

    def _parse_hierarchy(self, soup: BeautifulSoup) -> dict[str, dict]:
        """Build a mapping of article_number -> hierarchy context from the sidebar tree."""
        hierarchy: dict[str, dict] = {}
        current = {"part": None, "chapter": None, "section": None, "subsection": None}

        left = soup.select_one(SELECTORS_LAW["left_tree"])
        if not left:
            return hierarchy

        for item in left.select(SELECTORS_LAW["article_tree_item"]):
            text = item.get_text(strip=True)
            if re.match(r"제\d+편", text):
                current["part"] = text
                current["chapter"] = None
                current["section"] = None
                current["subsection"] = None
            elif re.match(r"제\d+장", text):
                current["chapter"] = text
                current["section"] = None
                current["subsection"] = None
            elif re.match(r"제\d+절", text):
                current["section"] = text
                current["subsection"] = None
            elif re.match(r"제\d+관", text):
                current["subsection"] = text
            elif m := re.match(r"(제\d+조(?:의\d+)?)", text):
                hierarchy[m.group(1)] = dict(current)

        return hierarchy

    def _extract_articles(self, body: BeautifulSoup, hierarchy: dict) -> list[StatuteArticle]:
        """Extract individual articles from the law body HTML."""
        articles: list[StatuteArticle] = []
        raw = body.get_text("\n")
        # Split on article boundaries: 제N조 or 제N조의N
        parts = re.split(r"(?=제\d+조(?:의\d+)?\s*[\(（])", raw)

        for part in parts:
            part = part.strip()
            if not part:
                continue
            m = re.match(r"(제\d+조(?:의\d+)?)\s*[\(（]([^)）]+)[\)）](.*)", part, re.DOTALL)
            if not m:
                continue

            article_num = m.group(1)
            title = m.group(2).strip()
            content_body = m.group(3).strip()
            full_content = f"{article_num}({title}) {content_body}"
            full_content = clean_html_text(full_content)

            ctx = hierarchy.get(article_num, {})

            articles.append(
                StatuteArticle(
                    source_key=self._source_key,
                    law_name=self._law_name,
                    part=ctx.get("part"),
                    chapter=ctx.get("chapter"),
                    section=ctx.get("section"),
                    subsection=ctx.get("subsection"),
                    article_number=article_num,
                    article_title=title,
                    content=full_content,
                )
            )

        return articles
