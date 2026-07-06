"""Sieve config: ~/.sieve/config.json + env var overrides."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

SIEVE_HOME = Path(os.environ.get("SIEVE_HOME", "~/.sieve")).expanduser()
BIN_DIR = SIEVE_HOME / "bin"
CONFIG_PATH = SIEVE_HOME / "config.json"
DB_PATH = SIEVE_HOME / "sieve.db"
SHIM_PATH = BIN_DIR / "claude"


class SieveConfig(BaseModel):
    real_claude_path: str | None = None
    shim_path: str = str(SHIM_PATH)
    enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    mode: Literal["auto", "local_only", "claude_only"] = "auto"
    max_context_chars: int = 20000
    debug: bool = False
    triage_method: Literal["heuristic", "llm"] = "heuristic"
    triage_model: str | None = None


def load_config() -> SieveConfig:
    cfg = SieveConfig()
    if CONFIG_PATH.exists():
        try:
            cfg = SieveConfig.model_validate_json(CONFIG_PATH.read_text())
        except (ValueError, OSError) as exc:
            # A corrupt config file must never brick every sieve command
            # (including the shim's pass-through to claude). Warn and run on
            # defaults; `sieve on` rewrites the file.
            print(f"sieve: ignoring corrupt config at {CONFIG_PATH}: {exc}", file=sys.stderr)

    # Env vars override the persisted file for a single invocation.
    overrides: dict[str, object] = {}
    if v := os.environ.get("SIEVE_MODE"):
        overrides["mode"] = v
    if v := os.environ.get("SIEVE_OLLAMA_BASE_URL"):
        overrides["ollama_base_url"] = v
    if v := os.environ.get("SIEVE_OLLAMA_MODEL"):
        overrides["ollama_model"] = v
    if v := os.environ.get("SIEVE_MAX_CONTEXT_CHARS"):
        overrides["max_context_chars"] = v
    if v := os.environ.get("SIEVE_DEBUG"):
        overrides["debug"] = v.strip().lower() in {"1", "true", "yes", "on"}
    if v := os.environ.get("SIEVE_TRIAGE_METHOD"):
        overrides["triage_method"] = v
    if v := os.environ.get("SIEVE_TRIAGE_MODEL"):
        overrides["triage_model"] = v

    if not overrides:
        return cfg

    try:
        # model_validate (not model_copy) so bad env values — SIEVE_MODE=garbage,
        # a non-numeric SIEVE_MAX_CONTEXT_CHARS — are rejected instead of routing
        # on an invalid mode string.
        return SieveConfig.model_validate({**cfg.model_dump(), **overrides})
    except ValueError as exc:
        print(f"sieve: ignoring invalid SIEVE_* env override: {exc}", file=sys.stderr)
        return cfg


def save_config(cfg: SieveConfig) -> None:
    SIEVE_HOME.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(cfg.model_dump_json(indent=2))


def ensure_sieve_home() -> None:
    SIEVE_HOME.mkdir(parents=True, exist_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
