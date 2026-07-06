"""Health checks for 'sieve doctor'. Informational only — never hard-exits,
so install.sh can safely run it before 'sieve on' has created anything yet."""

from __future__ import annotations

import sqlite3
import sys
from contextlib import closing

from sieve import ollama, shim
from sieve.config import DB_PATH, SIEVE_HOME, SieveConfig


def run_checks(cfg: SieveConfig) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    py_ok = sys.version_info >= (3, 11)
    results.append(("Python version", py_ok, f"{sys.version.split()[0]}"))

    results.append(("Sieve config dir", SIEVE_HOME.is_dir(), str(SIEVE_HOME)))

    real_claude = cfg.real_claude_path or shim.find_real_claude()
    results.append(("Real Claude binary", bool(real_claude), real_claude or "not found in PATH"))

    installed = shim.shim_installed()
    results.append(("Shim installed", installed, str(shim.SHIM_PATH) if installed else "not installed"))

    path_ok = shim.path_order_correct()
    results.append(
        (
            "PATH order",
            path_ok,
            "~/.sieve/bin precedes real claude" if path_ok else "run 'sieve on' for the export command",
        )
    )

    online = ollama.is_online(cfg.ollama_base_url)
    results.append(("Ollama reachable", online, cfg.ollama_base_url if online else "offline"))

    if online:
        model_ok = ollama.model_available(cfg.ollama_base_url, cfg.ollama_model)
        results.append(
            ("Ollama model available", model_ok, cfg.ollama_model if model_ok else f"pull it: ollama pull {cfg.ollama_model}")
        )
    else:
        results.append(("Ollama model available", False, "skipped — Ollama offline"))

    if cfg.triage_method == "llm":
        triage_model = cfg.triage_model or cfg.ollama_model
        if online and triage_model != cfg.ollama_model:
            triage_ok = ollama.model_available(cfg.ollama_base_url, triage_model)
            results.append(
                ("Triage model available", triage_ok, triage_model if triage_ok else f"pull it: ollama pull {triage_model}")
            )
        elif not online:
            results.append(("Triage model available", False, "skipped — Ollama offline"))
        # else: same model as ollama_model, already covered by the check above.

    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(DB_PATH)) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS _doctor_probe (x INTEGER)")
            conn.execute("DROP TABLE _doctor_probe")
            conn.commit()
        db_ok, db_detail = True, str(DB_PATH)
    except sqlite3.Error as exc:
        db_ok, db_detail = False, str(exc)
    results.append(("SQLite ledger writable", db_ok, db_detail))

    return results
