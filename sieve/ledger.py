"""SQLite ledger at ~/.sieve/sieve.db — stdlib sqlite3, no ORM needed for one table."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sieve.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    command TEXT,
    route TEXT NOT NULL,
    complexity INTEGER,
    confidence REAL,
    reason TEXT,
    context_mode TEXT,
    estimated_input_tokens INTEGER,
    estimated_output_tokens INTEGER,
    estimated_quota_saved INTEGER,
    latency_ms INTEGER,
    success INTEGER,
    error_message TEXT
);
"""


@dataclass
class RequestRecord:
    command: str
    route: str
    complexity: int
    confidence: float
    reason: str
    context_mode: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_quota_saved: int
    latency_ms: int
    success: bool
    error_message: str | None = None


def ensure_db(db_path=DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(SCHEMA)
        conn.commit()


def insert_request(record: RequestRecord, db_path=DB_PATH) -> None:
    ensure_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO requests (
                timestamp, command, route, complexity, confidence, reason,
                context_mode, estimated_input_tokens, estimated_output_tokens,
                estimated_quota_saved, latency_ms, success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                record.command,
                record.route,
                record.complexity,
                record.confidence,
                record.reason,
                record.context_mode,
                record.estimated_input_tokens,
                record.estimated_output_tokens,
                record.estimated_quota_saved,
                record.latency_ms,
                int(record.success),
                record.error_message,
            ),
        )
        conn.commit()


def get_summary(hours: float = 5.0, db_path=DB_PATH) -> dict:
    ensure_db(db_path)
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    with closing(sqlite3.connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT route, estimated_quota_saved, latency_ms FROM requests WHERE timestamp >= ?",
            (since,),
        ).fetchall()

    total = len(rows)
    local = sum(1 for r in rows if r[0] == "local")
    claude = sum(1 for r in rows if r[0] == "claude")
    quota_saved = sum(r[1] or 0 for r in rows)
    avg_latency_ms = sum(r[2] or 0 for r in rows) / total if total else 0.0

    return {
        "requests": total,
        "local": local,
        "claude": claude,
        "quota_preserved_tokens": quota_saved,
        "route_efficiency_local_pct": (local / total * 100) if total else 0.0,
        "avg_latency_s": avg_latency_ms / 1000,
    }


def get_history(limit: int = 20, db_path=DB_PATH) -> list[dict]:
    ensure_db(db_path)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM requests ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
