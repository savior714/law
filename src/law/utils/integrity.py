"""Hash-based content integrity verification."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import aiosqlite


def content_hash(text: str) -> str:
    """Return the SHA-256 hex digest of the given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def verify_table_integrity(
    db: aiosqlite.Connection,
    table: str,
    content_column: str = "content",
) -> tuple[int, int]:
    """Re-hash every record in *table* and compare with stored content_hash.

    Returns (total_checked, mismatches).
    Logs results into the integrity_log table.
    """
    rows = await db.execute_fetchall(
        f"SELECT id, {content_column}, content_hash FROM {table}"  # noqa: S608
    )

    now = datetime.now(timezone.utc).isoformat()
    mismatches = 0

    for row in rows:
        expected = content_hash(row[content_column])
        match = 1 if expected == row["content_hash"] else 0
        if not match:
            mismatches += 1
        await db.execute(
            "INSERT INTO integrity_log (table_name, record_id, checked_at, hash_match, details) "
            "VALUES (?, ?, ?, ?, ?)",
            (table, row["id"], now, match, None if match else f"expected={expected}"),
        )

    await db.commit()
    return len(rows), mismatches
