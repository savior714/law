"""Async CRUD operations for the SQLite database."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Literal, TypedDict, cast, Sequence

import aiosqlite

from law.config import DB_PATHS, SOURCES
from law.models.schemas import AdminRuleArticle, Precedent, StatuteArticle
from law.utils.integrity import content_hash

# --- Type Definitions ---
ShardKey = Literal["meta", "statutes", "precedents", "decisions"]
TableName = Literal["statutes", "admin_rules", "precedents", "scrape_runs"]

class ScrapeRunRecord(TypedDict):
    id: int
    source_key: str
    started_at: str
    finished_at: str | None
    status: Literal["running", "completed", "failed"]
    total_records: int
    error_message: str | None
    checkpoint: str | None

class Repository:
    """Async repository wrapping sharded SQLite operations."""

    def __init__(self) -> None:
        self._dbs: dict[ShardKey, aiosqlite.Connection] = {}

    async def connect(self) -> None:
        """Connect to all sharded databases."""
        for key, path in DB_PATHS.items():
            shard_key = cast(ShardKey, key)
            db = await aiosqlite.connect(path)
            db.row_factory = aiosqlite.Row
            self._dbs[shard_key] = db

    async def close(self) -> None:
        """Close all connections."""
        for db in self._dbs.values():
            await db.close()
        self._dbs.clear()

    def get_db(self, db_key: ShardKey) -> aiosqlite.Connection:
        """Retrieve connection for a specific shard."""
        if db_key not in self._dbs:
            raise RuntimeError(f"Database shard '{db_key}' not connected or invalid.")
        return self._dbs[db_key]

    def route_source(self, source_key: str) -> ShardKey:
        """Find the correct db_key for a given source."""
        if source_key in SOURCES:
            return cast(ShardKey, SOURCES[source_key].db_key)
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
        if cursor.lastrowid is None:
            raise RuntimeError("Failed to retrieve lastrowid after INSERT into scrape_runs.")
        return cursor.lastrowid

    async def finish_run(self, run_id: int, *, total: int, error: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        status: Literal["completed", "failed"] = "failed" if error else "completed"
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
            if row:
                val = row["checkpoint"]
                return str(val) if val is not None else None
            return None

    async def get_run_checkpoint(self, run_id: int) -> str | None:
        """Fetch checkpoint for a specific run."""
        db = self.get_db("meta")
        async with db.execute(
            "SELECT checkpoint FROM scrape_runs WHERE id=?", (run_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                val = row["checkpoint"]
                return str(val) if val is not None else None
            return None

    # ── Sync Stats ───────────────────────────────────────────────────

    async def get_last_sync_at(self, sync_key: str = "chromadb") -> str:
        """Get the last sync timestamp for a given target."""
        db = self.get_db("meta")
        async with db.execute(
            "SELECT last_sync_at FROM sync_stats WHERE sync_key=?", (sync_key,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return str(row["last_sync_at"])
            return "1970-01-01T00:00:00Z"  # Epoch default

    async def update_sync_at(self, sync_key: str = "chromadb", timestamp: str | None = None) -> None:
        """Update the last sync timestamp to the given ISO string or now."""
        val = timestamp or datetime.now(timezone.utc).isoformat()
        db = self.get_db("meta")
        await db.execute(
            "INSERT INTO sync_stats (sync_key, last_sync_at) VALUES (?, ?) "
            "ON CONFLICT(sync_key) DO UPDATE SET last_sync_at=excluded.last_sync_at",
            (sync_key, val),
        )
        await db.commit()

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

    async def fetch_all_statutes(self, since: str | None = None) -> Sequence[aiosqlite.Row]:
        query = "SELECT * FROM statutes"
        params = []
        if since:
            query += " WHERE scraped_at > ?"
            params.append(since)
        query += " ORDER BY source_key, id"
        return await self.get_db("statutes").execute_fetchall(query, params)

    async def fetch_all_admin_rules(self, since: str | None = None) -> Sequence[aiosqlite.Row]:
        query = "SELECT * FROM admin_rules"
        params = []
        if since:
            query += " WHERE scraped_at > ?"
            params.append(since)
        query += " ORDER BY id"
        return await self.get_db("statutes").execute_fetchall(query, params)

    async def fetch_all_precedents(self, since: str | None = None) -> Sequence[aiosqlite.Row]:
        """Fetch all precedents from both sharded databases, optionally since a timestamp."""
        query = "SELECT * FROM precedents"
        params = []
        if since:
            query += " WHERE scraped_at > ?"
            params.append(since)
            
        rows_p = await self.get_db("precedents").execute_fetchall(query, params)
        rows_d = await self.get_db("decisions").execute_fetchall(query, params)
        all_rows = list(rows_p) + list(rows_d)
        # Re-sort in memory
        all_rows.sort(key=lambda r: (r["source_key"], r["decision_date"] or ""), reverse=True)
        return all_rows

    async def count_records(self, table: TableName) -> int:
        if table == "statutes" or table == "admin_rules":
            db = self.get_db("statutes")
            rows = await db.execute_fetchall(f"SELECT COUNT(*) as cnt FROM {table}")
        elif table == "precedents":
            rows_p = await self.get_db("precedents").execute_fetchall("SELECT COUNT(*) as cnt FROM precedents")
            rows_d = await self.get_db("decisions").execute_fetchall("SELECT COUNT(*) as cnt FROM precedents")
            cnt_p = cast(int, rows_p[0]["cnt"])
            cnt_d = cast(int, rows_d[0]["cnt"])
            return cnt_p + cnt_d
        elif table == "scrape_runs":
            db = self.get_db("meta")
            rows = await db.execute_fetchall("SELECT COUNT(*) as cnt FROM scrape_runs")
        else:
            return 0
        return cast(int, rows[0]["cnt"])