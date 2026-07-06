import sqlite3
from contextlib import closing
from pathlib import Path

from sieve.ledger import RequestRecord, ensure_db, get_history, get_summary, insert_request


def _record(route: str, quota_saved: int = 100, latency_ms: int = 500) -> RequestRecord:
    return RequestRecord(
        command="claude test",
        route=route,
        model="qwen2.5-coder:7b" if route == "local" else "claude",
        complexity=2,
        confidence=0.9,
        reason="test",
        context_mode="prompt_only",
        estimated_input_tokens=50,
        estimated_output_tokens=50,
        estimated_quota_saved=quota_saved,
        latency_ms=latency_ms,
        success=True,
    )


def test_insert_and_summary(tmp_path: Path):
    db_path = tmp_path / "sieve.db"
    insert_request(_record("local", quota_saved=100), db_path=db_path)
    insert_request(_record("local", quota_saved=200), db_path=db_path)
    insert_request(_record("claude", quota_saved=0), db_path=db_path)

    summary = get_summary(hours=5.0, db_path=db_path)
    assert summary["requests"] == 3
    assert summary["local"] == 2
    assert summary["claude"] == 1
    assert summary["quota_preserved_tokens"] == 300
    assert round(summary["route_efficiency_local_pct"], 1) == 66.7


def test_history_returns_recent_rows_first(tmp_path: Path):
    db_path = tmp_path / "sieve.db"
    insert_request(_record("local"), db_path=db_path)
    insert_request(_record("claude"), db_path=db_path)

    rows = get_history(limit=10, db_path=db_path)
    assert len(rows) == 2
    assert rows[0]["route"] == "claude"  # most recent first
    assert rows[1]["route"] == "local"
    assert rows[0]["model"] == "claude"
    assert rows[1]["model"] == "qwen2.5-coder:7b"


def test_ensure_db_migrates_pre_model_column_schema(tmp_path: Path):
    db_path = tmp_path / "sieve.db"
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE requests (
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
            )
            """
        )
        conn.commit()

    ensure_db(db_path)  # should migrate in the missing 'model' column, not error

    insert_request(_record("local"), db_path=db_path)
    rows = get_history(limit=1, db_path=db_path)
    assert rows[0]["model"] == "qwen2.5-coder:7b"
