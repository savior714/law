"""Dataset builder: reads from SQLite and produces NotebookLM-compatible bundle files."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from law.config import BUNDLE_MAX_BYTES, BUNDLE_PREFIX_MAP, EXPORT_DIR
from law.db.repository import Repository
from law.export.formatter import format_admin_rule, format_precedent, format_statute

logger = logging.getLogger(__name__)


async def build_dataset(repo: Repository) -> dict[str, int]:
    """Build all NotebookLM bundle files from the database.

    Returns a dict of {table_name: record_count}.
    """
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    counts: dict[str, int] = {}

    # Statutes
    rows = await repo.fetch_all_statutes()
    counts["statutes"] = len(rows)
    _write_bundles(rows, format_statute, BUNDLE_PREFIX_MAP["statutes"])

    # Admin rules
    rows = await repo.fetch_all_admin_rules()
    counts["admin_rules"] = len(rows)
    _write_bundles(rows, format_admin_rule, BUNDLE_PREFIX_MAP["admin_rules"])

    # Precedents
    rows = await repo.fetch_all_precedents()
    counts["precedents"] = len(rows)
    _write_bundles(rows, format_precedent, BUNDLE_PREFIX_MAP["precedents"])

    # Master atlas index
    _write_master_atlas(counts)

    total = sum(counts.values())
    logger.info("Dataset build complete: %d total records", total)
    return counts


def _write_bundles(rows: list, formatter: callable, prefix: str) -> int:  # type: ignore[type-arg]
    """Split formatted records into bundle files respecting the size limit.

    Returns the number of bundle files created.
    """
    if not rows:
        return 0

    bundle_num = 1
    current_size = 0
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal bundle_num, current_size, current_lines
        if not current_lines:
            return
        path = EXPORT_DIR / f"{prefix}_{bundle_num:02d}.txt"
        path.write_text("\n".join(current_lines), encoding="utf-8")
        logger.info("Wrote %s (%d bytes)", path.name, current_size)
        bundle_num += 1
        current_size = 0
        current_lines = []

    for row in rows:
        block = formatter(row)
        block_bytes = len(block.encode("utf-8"))

        if current_size + block_bytes > BUNDLE_MAX_BYTES and current_lines:
            flush()

        current_lines.append(block)
        current_size += block_bytes

    flush()
    return bundle_num - 1


def _write_master_atlas(counts: dict[str, int]) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = sum(counts.values())

    content = f"""# [MASTER ATLAS] Korean Criminal Law Dataset (NotebookLM Edition)

**Protocol**: This dataset is optimized for NotebookLM RAG ingestion.
1. Search by statute name or case number.
2. Statute bundles contain full article text with hierarchy.
3. Precedent bundles contain holdings, summaries, and full text.

> Generated: {now} (Total: {total} records / {len(counts)} sources)

---

## Sources

| Bundle ID | Records | Prefix |
| :--- | :--- | :--- |
| **STATUTE** | {counts.get('statutes', 0)}건 | BUNDLE_STATUTE_XX.txt |
| **ADMIN_RULE** | {counts.get('admin_rules', 0)}건 | BUNDLE_ADMIN_RULE_XX.txt |
| **PRECEDENT** | {counts.get('precedents', 0)}건 | BUNDLE_PRECEDENT_XX.txt |
"""

    path = EXPORT_DIR / "00_MASTER_ATLAS.md"
    path.write_text(content, encoding="utf-8")
    logger.info("Wrote master atlas: %s", path.name)
