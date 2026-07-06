"""Installs the Sieve status-line badge into Claude Code's settings.json.

The badge script is embedded as a string rather than shipped as a separate
file: after a non-editable `pip install .`, sieve/ is copied into
site-packages and loses proximity to any repo-relative path, so this is the
one location that reliably works regardless of install mode.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

CLAUDE_CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", "~/.claude")).expanduser()
HOOKS_DIR = CLAUDE_CONFIG_DIR / "hooks"
SETTINGS_PATH = CLAUDE_CONFIG_DIR / "settings.json"
SCRIPT_PATH = HOOKS_DIR / "sieve-statusline.sh"

SCRIPT_CONTENT = """#!/bin/bash
# sieve — statusline badge for Claude Code.
# Shows [SIEVE] plus quota preserved in the last 5 hours (same window as
# `sieve ledger`). Renders nothing if Sieve isn't installed/enabled, or the
# ledger doesn't exist yet — safe default for machines without Sieve.

CONFIG="${SIEVE_HOME:-$HOME/.sieve}/config.json"
DB="${SIEVE_HOME:-$HOME/.sieve}/sieve.db"

# Refuse symlinks — a local attacker could point these at arbitrary files
# and leak bytes into the terminal.
[ -L "$CONFIG" ] && exit 0
[ ! -f "$CONFIG" ] && exit 0

ENABLED=$(grep -o '"enabled"[[:space:]]*:[[:space:]]*true' "$CONFIG")
[ -z "$ENABLED" ] && exit 0

printf '\\033[38;5;39m[SIEVE]\\033[0m'

[ -L "$DB" ] && exit 0
[ ! -f "$DB" ] && exit 0
command -v sqlite3 >/dev/null 2>&1 || exit 0

SINCE=$(date -u -v-5H +%Y-%m-%dT%H:%M:%S 2>/dev/null || date -u -d '5 hours ago' +%Y-%m-%dT%H:%M:%S 2>/dev/null)
[ -z "$SINCE" ] && exit 0

SAVED=$(sqlite3 "$DB" "SELECT COALESCE(SUM(estimated_quota_saved),0) FROM requests WHERE timestamp >= '$SINCE';" 2>/dev/null)

# Only ever a plain integer from SUM() — still guard against a corrupt/locked
# DB returning something unexpected before it reaches printf.
case "$SAVED" in
    ''|*[!0-9]*) exit 0 ;;
esac

[ "$SAVED" -le 0 ] && exit 0

if [ "$SAVED" -ge 1000 ]; then
    HUMAN=$(awk -v n="$SAVED" 'BEGIN{printf "%.1fK", n/1000}')
else
    HUMAN="$SAVED"
fi

printf ' \\033[38;5;39m\\xf0\\x9f\\xaa\\x99 %s\\033[0m' "$HUMAN"
"""


def write_script() -> Path:
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    SCRIPT_PATH.write_text(SCRIPT_CONTENT)
    SCRIPT_PATH.chmod(SCRIPT_PATH.stat().st_mode | 0o111)
    return SCRIPT_PATH


def install(settings_path: Path | None = None) -> str:
    """Writes the badge script and wires it into settings.json's statusLine,
    chaining with any existing command instead of clobbering it.
    Returns a short human-readable outcome."""
    write_script()

    settings_path = settings_path or SETTINGS_PATH
    settings = json.loads(settings_path.read_text()) if settings_path.exists() else {}

    sieve_cmd = f'bash "{SCRIPT_PATH}"'
    status_line = settings.get("statusLine")

    if not isinstance(status_line, dict) or status_line.get("type") != "command":
        settings["statusLine"] = {"type": "command", "command": sieve_cmd}
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")
        return "installed fresh statusLine"

    existing_cmd = status_line.get("command", "")
    if sieve_cmd in existing_cmd:
        return "already installed"

    status_line["command"] = f"{existing_cmd}; printf ' '; {sieve_cmd}" if existing_cmd else sieve_cmd
    settings["statusLine"] = status_line
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    return "chained into existing statusLine"
