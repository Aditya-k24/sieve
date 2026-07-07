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
# Shows [SIEVE:<model>] for whichever model handled the most recent request
# (local Ollama model name, a user-passed --model, or the session's own model).
# Renders nothing if Sieve isn't installed/enabled, or the ledger doesn't
# exist yet.

# Claude Code pipes session JSON to statusline commands on stdin; the model's
# display_name is the documented way to learn which model the session runs.
STDIN_JSON=$(cat 2>/dev/null)
SESSION_MODEL=$(printf '%s' "$STDIN_JSON" \\
    | sed -n 's/.*"display_name"[[:space:]]*:[[:space:]]*"\\([^"]*\\)".*/\\1/p' | head -1)

CONFIG="${SIEVE_HOME:-$HOME/.sieve}/config.json"
DB="${SIEVE_HOME:-$HOME/.sieve}/sieve.db"

# Refuse symlinks — a local attacker could point these at arbitrary files
# and leak bytes into the terminal.
[ -L "$CONFIG" ] && exit 0
[ ! -f "$CONFIG" ] && exit 0

ENABLED=$(grep -o '"enabled"[[:space:]]*:[[:space:]]*true' "$CONFIG")
[ -z "$ENABLED" ] && exit 0

LATEST_MODEL=""
if [ ! -L "$DB" ] && [ -f "$DB" ] && command -v sqlite3 >/dev/null 2>&1; then
    LATEST_MODEL=$(sqlite3 "$DB" "SELECT model FROM requests ORDER BY id DESC LIMIT 1;" 2>/dev/null)
fi

# A bare "claude" label means Sieve routed to Claude Code without knowing the
# model — the session's own display_name is strictly more informative.
if [ -z "$LATEST_MODEL" ] || [ "$LATEST_MODEL" = "claude" ]; then
    [ -n "$SESSION_MODEL" ] && LATEST_MODEL="$SESSION_MODEL"
fi

# Whitelist a safe charset before anything user-editable reaches printf —
# ollama_model comes from user-editable JSON, same reasoning as the symlink
# guards above. Space allowed for display names like "Fable 5".
LATEST_MODEL=$(printf '%s' "$LATEST_MODEL" | tr -cd 'A-Za-z0-9:_. /-' | cut -c1-40)

if [ -n "$LATEST_MODEL" ]; then
    printf '\\033[38;5;39m[SIEVE:%s]\\033[0m' "$LATEST_MODEL"
else
    printf '\\033[38;5;39m[SIEVE]\\033[0m'
fi
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
