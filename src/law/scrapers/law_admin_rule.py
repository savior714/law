"""Scraper for administrative rules on law.go.kr (범죄수사규칙 etc.).

Uses admRulInfoP.do template.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncGenerator

from bs4 import BeautifulSoup

from law.config import SELECTORS_LAW, SOURCES
from law.models.schemas import AdminRuleArticle
from law.scrapers.base import BaseScraper, SelectorNotFoundError
from law.utils.text import clean_html_text

logger = logging.getLogger(__name__)


class AdminRuleScraper(BaseScraper):
    """Scrapes administrative rule articles from law.go.kr using structural extraction."""

    def __init__(self, source_key: str) -> None:
        super().__init__()
        src = SOURCES[source_key]
        self.name = source_key
        self.source_url = src["url"]
        self._rule_name = src["name"]
        self._source_key = source_key

    async def validate_page_loaded(self) -> bool:
        body = SELECTORS_LAW["law_body"]
        alt = SELECTORS_LAW["body_content"]
        el = await self.page.query_selector(body) or await self.page.query_selector(alt) or await self.page.query_selector("#bodyId")
        if el is None:
            raise SelectorNotFoundError(f"{self.name}: neither {body} nor {alt} found")
        return True

    async def _wait_for_law_body(self, timeout: int = 30_000) -> None:
        """Wait until main content has actual text content."""
        deadline = asyncio.get_event_loop().time() + (timeout / 1000)
        while asyncio.get_event_loop().time() < deadline:
            has_content = await self.page.evaluate("""() => {
                const el = document.querySelector('#lsBdy') || document.querySelector('#bodyContent') || document.querySelector('#conScroll');
                return el && el.innerText.trim().length > 100;
            }""")
            if has_content:
                return
            await asyncio.sleep(0.5)

    async def scrape(self) -> AsyncGenerator[AdminRuleArticle, None]:
        await self.safe_navigate(self.source_url)
        await self._wait_for_law_body()
        await self.validate_page_loaded()

        # Step 1: Collect attachments
        attachments = await self._scrape_attachments()

        # Step 2: Extract Hierarchy
        html = await self.get_page_content()
        soup = BeautifulSoup(html, "lxml")
        hierarchy = self._extract_hierarchy(soup)

        # Step 3: Structural Article Extraction
        logger.info("%s: performing structural article extraction...", self.name)
        extracted_data = await self.page.evaluate("""() => {
            const results = [];
            const container = document.querySelector('#bodyContent') || document.querySelector('#lsBdy') || document.querySelector('#conScroll');
            if (!container) return [];

            const allElements = Array.from(container.querySelectorAll('div, p'));
            let currentArticle = null;
            let currentAddendum = null;

            for (const el of allElements) {
                const txt = el.innerText.trim();
                if (!txt || txt.length < 2) continue;

                if (txt.includes('부 칙')) {
                    const m = txt.match(/부\s*칙\s*[<＜]([^>＞]+)[>＞]/);
                    currentAddendum = m ? m[1] : "기본";
                    continue;
                }

                // Match Article Header: "제1조(목적)"
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
                    if (!currentArticle.content.includes(txt)) {
                        currentArticle.content += "\\n" + txt;
                    }
                }
            }
            if (currentArticle) results.push(currentArticle);
            return results;
        }""")

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

            clean_content = clean_html_text(content)
            ctx = hierarchy.get(art_num, {})
            
            article = AdminRuleArticle(
                source_key=self._source_key,
                rule_name=self._rule_name,
                part=ctx.get("part"),
                chapter=ctx.get("chapter"),
                section=ctx.get("section"),
                article_number=art_num_display,
                article_title=title,
                content=clean_content,
                attachments=attachments if i == 0 else [],
            )
            all_articles.append(article)
            yield article

        logger.info("%s: successfully extracted %d articles structurally", self.name, len(all_articles))

    def _extract_hierarchy(self, soup: BeautifulSoup) -> dict[str, dict]:
        """Build hierarchy mapping for administrative rules."""
        hierarchy: dict[str, dict] = {}
        current = {"part": None, "chapter": None, "section": None}

        left = soup.select_one(SELECTORS_LAW["left_tree"])
        if not left:
            return hierarchy

        for item in left.select(SELECTORS_LAW["article_tree_item"]):
            text = item.get_text(strip=True)
            if re.match(r"제\d+편", text):
                current["part"] = text
                current["chapter"] = None
                current["section"] = None
            elif re.match(r"제\d+장", text):
                current["chapter"] = text
                current["section"] = None
            elif re.match(r"제\d+절", text):
                current["section"] = text
            elif m := re.match(r"(제\d+조(?:의\d+)?)", text):
                hierarchy[m.group(1)] = dict(current)

        return hierarchy
