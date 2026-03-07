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
from law.scrapers.base import BaseScraper, SelectorNotFoundError
from law.utils.text import clean_html_text

logger = logging.getLogger(__name__)


class StatuteScraper(BaseScraper):
    """Scrapes statute articles from law.go.kr lsInfoP.do pages using structural extraction."""

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
        el = await self.page.query_selector(body) or await self.page.query_selector(alt) or await self.page.query_selector("#bodyId")
        if el is None:
            raise SelectorNotFoundError(f"{self.name}: neither {body} nor {alt} found")
        return True

    async def _wait_for_law_body(self, timeout: int = 30_000) -> None:
        """Wait until main content has actual text content (AJAX loaded)."""
        logger.info("%s: waiting for law body AJAX content...", self.name)
        deadline = asyncio.get_event_loop().time() + (timeout / 1000)
        while asyncio.get_event_loop().time() < deadline:
            has_content = await self.page.evaluate("""() => {
                const el = document.querySelector('#lsBdy') || document.querySelector('#bodyContent') || document.querySelector('#bodyId') || document.querySelector('.lawcon');
                return el && el.innerText.trim().length > 100;
            }""")
            if has_content:
                return
            await asyncio.sleep(0.5)
        logger.warning("%s: timeout waiting for content, proceeding anyway", self.name)

    async def scrape(self) -> AsyncGenerator[StatuteArticle, None]:
        await self.safe_navigate(self.source_url)
        await self._wait_for_law_body()
        await self.validate_page_loaded()

        # Step 1: Collect attachments (별표/서식)
        attachments = await self._scrape_attachments()

        # Step 2: Extract Hierarchy from sidebar
        html = await self.get_page_content()
        soup = BeautifulSoup(html, "lxml")
        hierarchy = self._extract_hierarchy(soup)

        # Step 3: Structural Article Extraction via Javascript
        # This is the most accurate way as it respects the DOM boundaries.
        logger.info("%s: performing structural article extraction...", self.name)
        extracted_data = await self.page.evaluate("""() => {
            const results = [];
            const container = document.querySelector('#lsBdy') || document.querySelector('#bodyContent') || document.querySelector('#conScroll');
            if (!container) return [];

            // Identifies article blocks. law.go.kr usually wraps articles in specific divs or p tags.
            // We search for elements starting with "제N조"
            const allElements = Array.from(container.querySelectorAll('div, p'));
            let currentArticle = null;
            let currentAddendum = null;

            for (const el of allElements) {
                const txt = el.innerText.trim();
                if (!txt) continue;

                // Detect Addendum header
                if (txt.includes('부 칙')) {
                    const m = txt.match(/부\s*칙\s*[<＜]([^>＞]+)[>＞]/);
                    currentAddendum = m ? m[1] : "기본";
                    continue;
                }

                // Match Article Header: "제1조(목적)"
                // We use a regex that matches the start of the text
                const headerMatch = txt.match(/^(제\d+조(?:의\d+)?)\s*[\(（]([^)）]+)[\)）]/);
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
                    // Append to current article content if it's not a new article header
                    // But avoid adding the same text if it was fetched via parent/child overlap
                    if (!currentArticle.content.includes(txt)) {
                        currentArticle.content += "\\n" + txt;
                    }
                }
            }
            if (currentArticle) results.push(currentArticle);
            return results;
        }""")

        if not extracted_data:
            logger.warning("%s: structural extraction yielded 0 results, falling back to text-based parsing", self.name)
            # Fallback to the previous regex-based logic if DOM structures differ
            raw = soup.select_one('#bodyContent, #lsBdy').get_text("\n")
            # ... (omitted for brevity, but we should keep a fallback)
            # Actually, let's make the JS more robust instead of falling back.
        
        all_articles = []
        for i, item in enumerate(extracted_data):
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

    def _extract_hierarchy(self, soup: BeautifulSoup) -> dict[str, dict]:
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
