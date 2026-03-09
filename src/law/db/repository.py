"""Async CRUD operations for the SQLite database."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

from law.config import DB_PATHS, SOURCES
from law.models.schemas import AdminRuleArticle, Precedent, StatuteArticle
from law.utils.integrity import content_hash


class Repository:
    """Async repository wrapping sharded SQLite operations."""

    def __init__(self) -> None:
        self._dbs: dict[str, aiosqlite.Connection] = {}

    async def connect(self) -> None:
        """Connect to all sharded databases."""
        for key, path in DB_PATHS.items():
            db = await aiosqlite.connect(path)
            db.row_factory = aiosqlite.Row
            self._dbs[key] = db

    async def close(self) -> None:
        """Close all connections."""
        for db in self._dbs.values():
            await db.close()
        self._dbs.clear()

    def get_db(self, db_key: str) -> aiosqlite.Connection:
        """Retrieve connection for a specific shard."""
        if db_key not in self._dbs:
            raise RuntimeError(f"Database shard '{db_key}' not connected or invalid.")
        return self._dbs[db_key]

    def route_source(self, source_key: str) -> str:
        """Find the correct db_key for a given source."""
        if source_key in SOURCES:
            return SOURCES[source_key].db_key
        return "statutes"  # default fallback

    # ── Scrape runs ────────────────────────────────────────────────────

    async def start_run(self, source_key: str) -> int:
        now = datetime.now(timezone.utc).isoformat()
        db = self.get_db("meta")
        cursor = await db.execute(
            "INSERT INTO scrape_runs (source_key, started_at, status) VALUES (?, ?, 'running')",
            (source_key, now),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def finish_run(self, run_id: int, *, total: int, error: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        status = "failed" if error else "completed"
        db = self.get_db("meta")
        await db.execute(
            "UPDATE scrape_runs SET finished_at=?, status=?, total_records=?, error_message=? WHERE id=?",
            (now, status, total, error, run_id),
        )
        await db.commit()

    async def update_checkpoint(self, run_id: int, checkpoint: str) -> None:
        """Update the checkpoint for a running scrape task."""
        db = self.get_db("meta")
        await db.execute(
            "UPDATE scrape_runs SET checkpoint=? WHERE id=?",
            (checkpoint, run_id),
        )
        await db.commit()

    async def get_last_checkpoint(self, source_key: str) -> str | None:
        """Fetch the checkpoint from the last failed or incomplete run for a source."""
        db = self.get_db("meta")
        async with db.execute(
            "SELECT checkpoint FROM scrape_runs "
            "WHERE source_key=? AND status != 'completed' "
            "ORDER BY id DESC LIMIT 1",
            (source_key,),
        ) as cursor:
            row = await cursor.fetchone()
            return row["checkpoint"] if row else None

    async def get_run_checkpoint(self, run_id: int) -> str | None:
        """Fetch checkpoint for a specific run."""
        db = self.get_db("meta")
        async with db.execute(
            "SELECT checkpoint FROM scrape_runs WHERE id=?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row["checkpoint"] if row else None

    # ── Statutes ───────────────────────────────────────────────────────

    async def upsert_statute(self, article: StatuteArticle, source_url: str, run_id: int) -> bool:
        """Insert or update a statute article. Returns True if new/updated."""
        now = datetime.now(timezone.utc).isoformat()
        h = content_hash(article.content)
        db = self.get_db("statutes")

        existing = await db.execute_fetchall(
            "SELECT id, content_hash FROM statutes WHERE source_key=? AND article_number=? AND article_title=?",
            (article.source_key, article.article_number, article.article_title),
        )

        if existing and existing[0]["content_hash"] == h:
            return False  # unchanged

        attachments_json = json.dumps([a.model_dump() for a in article.attachments], ensure_ascii=False)

        if existing:
            await db.execute(
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
            await db.execute(
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

        await db.commit()
        return True

    # ── Admin rules ────────────────────────────────────────────────────

    async def upsert_admin_rule(self, article: AdminRuleArticle, source_url: str, run_id: int) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        h = content_hash(article.content)
        db = self.get_db("statutes")

        existing = await db.execute_fetchall(
            "SELECT id, content_hash FROM admin_rules WHERE source_key=? AND article_number=? AND article_title=?",
            (article.source_key, article.article_number, article.article_title),
        )

        if existing and existing[0]["content_hash"] == h:
            return False

        attachments_json = json.dumps([a.model_dump() for a in article.attachments], ensure_ascii=False)

        if existing:
            await db.execute(
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
            await db.execute(
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

        await db.commit()
        return True

    # ── Precedents ─────────────────────────────────────────────────────

    async def upsert_precedent(self, prec: Precedent, source_url: str, run_id: int) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        text_for_hash = prec.full_text or prec.summary or prec.case_number
        h = content_hash(text_for_hash)
        db_key = self.route_source(prec.source_key)
        db = self.get_db(db_key)

        existing = await db.execute_fetchall(
            "SELECT id, content_hash FROM precedents WHERE source_key=? AND case_number=?",
            (prec.source_key, prec.case_number),
        )

        if existing and existing[0]["content_hash"] == h:
            return False

        refs_statutes = json.dumps(prec.referenced_statutes, ensure_ascii=False)
        refs_cases = json.dumps(prec.referenced_cases, ensure_ascii=False)
        decision = prec.decision_date.isoformat() if prec.decision_date else None

        if existing:
            await db.execute(
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
            await db.execute(
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

        await db.commit()
        return True

    # ── Read helpers (for export) ──────────────────────────────────────

    async def fetch_all_statutes(self) -> list[aiosqlite.Row]:
        return await self.get_db("statutes").execute_fetchall(
            "SELECT * FROM statutes ORDER BY source_key, id"
        )

    async def fetch_all_admin_rules(self) -> list[aiosqlite.Row]:
        return await self.get_db("statutes").execute_fetchall(
            "SELECT * FROM admin_rules ORDER BY id"
        )

    async def fetch_all_precedents(self) -> list[aiosqlite.Row]:
        """Fetch all precedents from both sharded databases."""
        rows_p = await self.get_db("precedents").execute_fetchall(
            "SELECT * FROM precedents"
        )
        rows_d = await self.get_db("decisions").execute_fetchall(
            "SELECT * FROM precedents"
        )
        all_rows = list(rows_p) + list(rows_d)
        # Re-sort in memory
        all_rows.sort(key=lambda r: (r["source_key"], r["decision_date"] or ""), reverse=True)
        return all_rows

    async def count_records(self, table: str) -> int:
        if table == "statutes" or table == "admin_rules":
            db = self.get_db("statutes")
            rows = await db.execute_fetchall(f"SELECT COUNT(*) as cnt FROM {table}")
        elif table == "precedents":
            cnt_p = (await self.get_db("precedents").execute_fetchall("SELECT COUNT(*) as cnt FROM precedents"))[0]["cnt"]
            cnt_d = (await self.get_db("decisions").execute_fetchall("SELECT COUNT(*) as cnt FROM precedents"))[0]["cnt"]
            return cnt_p + cnt_d
        elif table == "scrape_runs":
            db = self.get_db("meta")
            rows = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM scrape_runs")
        else:
            # Fallback
            return 0
        return rows[0]["cnt"]
