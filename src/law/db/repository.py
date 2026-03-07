"""Async CRUD operations for the SQLite database."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

from law.config import DB_PATH
from law.models.schemas import AdminRuleArticle, Precedent, StatuteArticle
from law.utils.integrity import content_hash


class Repository:
    """Async repository wrapping SQLite operations."""

    def __init__(self) -> None:
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(DB_PATH)
        self._db.row_factory = aiosqlite.Row

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Repository not connected. Call connect() first.")
        return self._db

    # ── Scrape runs ────────────────────────────────────────────────────

    async def start_run(self, source_key: str) -> int:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            "INSERT INTO scrape_runs (source_key, started_at, status) VALUES (?, ?, 'running')",
            (source_key, now),
        )
        await self.db.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def finish_run(self, run_id: int, *, total: int, error: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        status = "failed" if error else "completed"
        await self.db.execute(
            "UPDATE scrape_runs SET finished_at=?, status=?, total_records=?, error_message=? WHERE id=?",
            (now, status, total, error, run_id),
        )
        await self.db.commit()

    # ── Statutes ───────────────────────────────────────────────────────

    async def upsert_statute(self, article: StatuteArticle, source_url: str, run_id: int) -> bool:
        """Insert or update a statute article. Returns True if new/updated."""
        now = datetime.now(timezone.utc).isoformat()
        h = content_hash(article.content)

        existing = await self.db.execute_fetchall(
            "SELECT id, content_hash FROM statutes WHERE source_key=? AND article_number=? AND article_title=?",
            (article.source_key, article.article_number, article.article_title),
        )

        if existing and existing[0]["content_hash"] == h:
            return False  # unchanged

        attachments_json = json.dumps([a.model_dump() for a in article.attachments], ensure_ascii=False)

        if existing:
            await self.db.execute(
                "UPDATE statutes SET law_name=?, part=?, chapter=?, section=?, subsection=?, "
                "content=?, content_hash=?, source_url=?, scraped_at=?, scrape_run_id=?, "
                "attachments=? "
                "WHERE source_key=? AND article_number=? AND article_title=?",
                (
                    article.law_name, article.part, article.chapter, article.section,
                    article.subsection, article.content, h,
                    source_url, now, run_id, attachments_json, article.source_key, article.article_number, article.article_title,
                ),
            )
        else:
            await self.db.execute(
                "INSERT INTO statutes "
                "(source_key, law_name, part, chapter, section, subsection, article_number, "
                "article_title, content, content_hash, source_url, scraped_at, scrape_run_id, attachments) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    article.source_key, article.law_name, article.part, article.chapter,
                    article.section, article.subsection, article.article_number,
                    article.article_title, article.content, h, source_url, now, run_id, attachments_json,
                ),
            )

        await self.db.commit()
        return True

    # ── Admin rules ────────────────────────────────────────────────────

    async def upsert_admin_rule(self, article: AdminRuleArticle, source_url: str, run_id: int) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        h = content_hash(article.content)

        existing = await self.db.execute_fetchall(
            "SELECT id, content_hash FROM admin_rules WHERE source_key=? AND article_number=? AND article_title=?",
            (article.source_key, article.article_number, article.article_title),
        )

        if existing and existing[0]["content_hash"] == h:
            return False

        attachments_json = json.dumps([a.model_dump() for a in article.attachments], ensure_ascii=False)

        if existing:
            await self.db.execute(
                "UPDATE admin_rules SET rule_name=?, part=?, chapter=?, section=?, "
                "content=?, content_hash=?, source_url=?, scraped_at=?, scrape_run_id=?, "
                "attachments=? "
                "WHERE source_key=? AND article_number=? AND article_title=?",
                (
                    article.rule_name, article.part, article.chapter, article.section,
                    article.content, h,
                    source_url, now, run_id, attachments_json, article.source_key, article.article_number, article.article_title,
                ),
            )
        else:
            await self.db.execute(
                "INSERT INTO admin_rules "
                "(source_key, rule_name, part, chapter, section, article_number, "
                "article_title, content, content_hash, source_url, scraped_at, scrape_run_id, attachments) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    article.source_key, article.rule_name, article.part, article.chapter,
                    article.section, article.article_number,
                    article.article_title, article.content, h, source_url, now, run_id, attachments_json,
                ),
            )

        await self.db.commit()
        return True

    # ── Precedents ─────────────────────────────────────────────────────

    async def upsert_precedent(self, prec: Precedent, source_url: str, run_id: int) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        text_for_hash = prec.full_text or prec.summary or prec.case_number
        h = content_hash(text_for_hash)

        existing = await self.db.execute_fetchall(
            "SELECT id, content_hash FROM precedents WHERE source_key=? AND case_number=?",
            (prec.source_key, prec.case_number),
        )

        if existing and existing[0]["content_hash"] == h:
            return False

        refs_statutes = json.dumps(prec.referenced_statutes, ensure_ascii=False)
        refs_cases = json.dumps(prec.referenced_cases, ensure_ascii=False)
        decision = prec.decision_date.isoformat() if prec.decision_date else None

        if existing:
            await self.db.execute(
                "UPDATE precedents SET case_name=?, court=?, decision_date=?, case_type=?, "
                "holding=?, summary=?, full_text=?, referenced_statutes=?, referenced_cases=?, "
                "content_hash=?, source_url=?, scraped_at=?, scrape_run_id=? "
                "WHERE source_key=? AND case_number=?",
                (
                    prec.case_name, prec.court, decision, prec.case_type,
                    prec.holding, prec.summary, prec.full_text,
                    refs_statutes, refs_cases, h, source_url, now, run_id,
                    prec.source_key, prec.case_number,
                ),
            )
        else:
            await self.db.execute(
                "INSERT INTO precedents "
                "(source_key, case_number, case_name, court, decision_date, case_type, "
                "holding, summary, full_text, referenced_statutes, referenced_cases, "
                "content_hash, source_url, scraped_at, scrape_run_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    prec.source_key, prec.case_number, prec.case_name, prec.court,
                    decision, prec.case_type, prec.holding, prec.summary,
                    prec.full_text, refs_statutes, refs_cases, h,
                    source_url, now, run_id,
                ),
            )

        await self.db.commit()
        return True

    # ── Read helpers (for export) ──────────────────────────────────────

    async def fetch_all_statutes(self) -> list[aiosqlite.Row]:
        return await self.db.execute_fetchall(
            "SELECT * FROM statutes ORDER BY source_key, id"
        )

    async def fetch_all_admin_rules(self) -> list[aiosqlite.Row]:
        return await self.db.execute_fetchall(
            "SELECT * FROM admin_rules ORDER BY id"
        )

    async def fetch_all_precedents(self) -> list[aiosqlite.Row]:
        return await self.db.execute_fetchall(
            "SELECT * FROM precedents ORDER BY source_key, decision_date DESC"
        )

    async def count_records(self, table: str) -> int:
        rows = await self.db.execute_fetchall(f"SELECT COUNT(*) as cnt FROM {table}")  # noqa: S608
        return rows[0]["cnt"]
