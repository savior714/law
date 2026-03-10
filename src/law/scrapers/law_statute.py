"""Scraper for statutes on law.go.kr (형법, 형사소송법, 경찰관직무집행법).

All three share the lsInfoP.do page template.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncGenerator

from bs4 import BeautifulSoup

from law.config import SELECTORS_LAW, SOURCES
from law.models.schemas import StatuteArticle
from law.scrapers.base import ScrapedItem
from law.scrapers.law_go_kr_base import LawGoKrScraper
from law.utils.text import clean_html_text

logger = logging.getLogger(__name__)


class StatuteScraper(LawGoKrScraper):
    """Scrapes statute articles from law.go.kr lsInfoP.do pages using structural extraction."""

    def __init__(self, source_key: str) -> None:
        super().__init__()
        src = SOURCES[source_key]
        self.name = source_key
        self.source_url = src.url
        self._law_name = src.name
        self._source_key = source_key

    async def scrape(self) -> AsyncGenerator[ScrapedItem, None]:
        await self.safe_navigate(self.source_url)
        await self._wait_for_law_body()
        await self.validate_page_loaded()

        # Step 1: Collect attachments (별표/서식)
        attachments = await self._scrape_attachments()

        # Step 2: Extract Hierarchy from sidebar
        html = await self.get_page_content()
        soup = BeautifulSoup(html, "lxml")
        hierarchy = self._extract_hierarchy_map(soup, ["part", "chapter", "section", "subsection"])

        # Step 3: Structural Article Extraction
        extracted_data = await self._extract_structural_articles()
        
        # Checkpoint: Resume if needed
        last_index = -1
        if self.resume_checkpoint:
            try:
                if self.resume_checkpoint == "completed":
                    logger.info("%s: already completed in previous run, skipping", self.name)
                    return
                last_index = int(self.resume_checkpoint)
                logger.info("%s: resuming from index %d", self.name, last_index)
            except ValueError:
                pass

        all_articles = []
        for i, item in enumerate(extracted_data):
            if i <= last_index:
                continue

            art_num = item["number"]
            title = item["title"]
            content = item["content"]
            is_add = item["is_addendum"]
            add_name = item["addendum_name"]

            if is_add:
                prefix = f"[부칙 <{add_name}>]" if add_name and add_name != "기본" else "[부칙]"
                art_num_display = f"{prefix} {art_num}"
            else:
                art_num_display = art_num

            # Final cleaning
            clean_content = clean_html_text(content)
            
            ctx = hierarchy.get(art_num, {})
            
            article = StatuteArticle(
                source_key=self._source_key,
                law_name=self._law_name,
                part=ctx.get("part"),
                chapter=ctx.get("chapter"),
                section=ctx.get("section"),
                subsection=ctx.get("subsection"),
                article_number=art_num_display,
                article_title=title,
                content=clean_content,
                attachments=attachments if i == 0 else [], # Attach to first
            )
            all_articles.append(article)
            yield article

        logger.info("%s: successfully extracted %d articles structurally", self.name, len(all_articles))

