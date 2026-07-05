"""Creates/removes the ~/.sieve/bin/claude shim and discovers the real Claude binary."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from sieve.config import BIN_DIR, SHIM_PATH

SHIM_SCRIPT = """#!/usr/bin/env bash
exec sieve run claude "$@"
"""


def find_real_claude(path_env: str | None = None) -> str | None:
    """Searches PATH for a 'claude' executable, skipping Sieve's own bin dir
    so 'sieve on' never detects its own shim as the real binary."""
    path_env = path_env if path_env is not None else os.environ.get("PATH", "")
    bin_dir_resolved = BIN_DIR.resolve()

    for entry in path_env.split(os.pathsep):
        if not entry:
            continue
        entry_path = Path(entry)
        try:
            if entry_path.resolve() == bin_dir_resolved:
                continue
        except OSError:
            continue
        candidate = entry_path / "claude"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def write_shim() -> Path:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    SHIM_PATH.write_text(SHIM_SCRIPT)
    SHIM_PATH.chmod(SHIM_PATH.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return SHIM_PATH


def remove_shim() -> bool:
    if SHIM_PATH.exists():
        SHIM_PATH.unlink()
        return True
    return False


def shim_installed() -> bool:
    return SHIM_PATH.is_file() and os.access(SHIM_PATH, os.X_OK)


def path_order_correct(path_env: str | None = None) -> bool:
    """True if BIN_DIR appears in PATH before any other 'claude' binary's dir."""
    path_env = path_env if path_env is not None else os.environ.get("PATH", "")
    bin_dir_resolved = BIN_DIR.resolve()
    for entry in path_env.split(os.pathsep):
        if not entry:
            continue
        entry_path = Path(entry)
        try:
            resolved = entry_path.resolve()
        except OSError:
            continue
        if resolved == bin_dir_resolved:
            return True
        if (entry_path / "claude").is_file():
            return False
    return False
