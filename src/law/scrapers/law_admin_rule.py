"""Generic scraper for administrative rules on law.go.kr (admRulInfoP.do template)."""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncGenerator

from bs4 import BeautifulSoup

from law.config import SELECTORS_LAW, SOURCES
from law.models.schemas import AdminRuleArticle, Attachment
from law.scrapers.base import BaseScraper, SelectorNotFoundError
from law.utils.text import clean_html_text

logger = logging.getLogger(__name__)


class AdminRuleScraper(BaseScraper):
    """Scrapes administrative rule articles from law.go.kr admRulInfoP.do."""

    def __init__(self, source_key: str) -> None:
        super().__init__()
        src = SOURCES[source_key]
        self.name = source_key
        self.source_url = src["url"]
        self._rule_name = src["name"]
        self._source_key = source_key

    async def validate_page_loaded(self) -> bool:
        sel = SELECTORS_LAW["admin_body_content"]
        el = await self.page.query_selector(sel)
        if el is None:
            raise SelectorNotFoundError(f"{self.name}: {sel} not found")
        return True

    async def scrape(self) -> AsyncGenerator[AdminRuleArticle, None]:
        await self.safe_navigate(self.source_url, wait_selector=SELECTORS_LAW["admin_body_content"])
        await self.validate_page_loaded()

        # Step 1: Collect attachments (별표/서식) using base method
        attachments = await self._scrape_attachments()

        html = await self.get_page_content()
        soup = BeautifulSoup(html, "lxml")

        body_el = soup.select_one(SELECTORS_LAW["admin_body_content"])
        if body_el is None:
            return

        # Decompose sidebar, controls and UI layers if they are inside body_el
        noise_selectors = [
            "#leftContent", "#lawContls", ".ls_btn", 
            ".p_layer_copy", "[class*='layer_copy']",
            "#lsByl", ".ls_sms_list", ".pconfile", ".note_list"
        ]
        for ns in noise_selectors:
            for noise in body_el.select(ns):
                noise.decompose()
                
        # Split by article marker
        raw = body_el.get_text("\n")
        
        # Split 본칙 vs 부칙
        main_body_text = raw
        addendum_text = ""
        
        if "부칙" in raw:
            if "\n부칙\n" in raw:
                parts_body = raw.split("\n부칙\n", 1)
                main_body_text = parts_body[0]
                addendum_text = parts_body[1]
            elif "부      칙" in raw:
                parts_body = raw.split("부      칙", 1)
                main_body_text = parts_body[0]
                addendum_text = parts_body[1]

        all_articles: list[AdminRuleArticle] = []
        current_ctx: dict[str, str | None] = {"part": None, "chapter": None, "section": None}

        def parse_text_to_articles(text: str, is_addendum: bool = False) -> list[AdminRuleArticle]:
            results = []
            # Split by "제N조"
            item_parts = re.split(r"(?=제\d+조(?:의\d+)?\s*[\(（])", text)
            
            for part in item_parts:
                part = part.strip()
                if not part: continue
                
                # Track hierarchy markers
                for line in part.split("\n"):
                    line = line.strip()
                    if re.match(r"제\d+편", line):
                        current_ctx["part"] = line
                        current_ctx["chapter"] = None
                        current_ctx["section"] = None
                    elif re.match(r"제\d+장", line):
                        current_ctx["chapter"] = line
                        current_ctx["section"] = None
                    elif re.match(r"제\d+절", line):
                        current_ctx["section"] = line

                # Match "제1조(목적) ..."
                m = re.match(r"(제\d+조(?:의\d+)?)\s*[\(（]([^)）]+)[\)）](.*)", part, re.DOTALL)
                if not m: continue
                
                article_num = m.group(1).strip()
                if is_addendum:
                    article_num = f"[부칙] {article_num}"
                    
                title = m.group(2).strip()
                content_body = m.group(3).strip()
                full_content = f"{article_num}({title})\n{content_body}"
                full_content = clean_html_text(full_content)

                results.append(
                    AdminRuleArticle(
                        source_key=self._source_key,
                        rule_name=self._rule_name,
                        part=current_ctx.get("part"),
                        chapter=current_ctx.get("chapter"),
                        section=current_ctx.get("section"),
                        article_number=article_num,
                        article_title=title,
                        content=full_content,
                        attachments=attachments if not all_articles and not results else [],
                    )
                )
            return results

        main_articles = parse_text_to_articles(main_body_text, is_addendum=False)
        all_articles.extend(main_articles)
        addendum_articles = parse_text_to_articles(addendum_text, is_addendum=True)
        all_articles.extend(addendum_articles)

        for article in all_articles:
            yield article

        logger.info("%s: extracted %d articles", self.name, len(all_articles))
