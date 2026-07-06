#!/bin/bash
# sieve — statusline badge for Claude Code.
# Shows [SIEVE] plus quota preserved in the last 5 hours (same window as
# `sieve ledger`). Renders nothing if Sieve isn't installed/enabled, or the
# ledger doesn't exist yet — safe default for machines without Sieve.
#
# Wire into ~/.claude/settings.json:
#   "statusLine": { "type": "command", "command": "bash /path/to/sieve-statusline.sh" }
# To combine with another badge (e.g. caveman), chain both commands with a
# separator, e.g.:
#   "command": "bash /path/to/other-statusline.sh; printf ' '; bash /path/to/sieve-statusline.sh"

CONFIG="${SIEVE_HOME:-$HOME/.sieve}/config.json"
DB="${SIEVE_HOME:-$HOME/.sieve}/sieve.db"

# Refuse symlinks — same reasoning as caveman's statusline: a local attacker
# could point these at arbitrary files and leak bytes into the terminal.
[ -L "$CONFIG" ] && exit 0
[ ! -f "$CONFIG" ] && exit 0

ENABLED=$(grep -o '"enabled"[[:space:]]*:[[:space:]]*true' "$CONFIG")
[ -z "$ENABLED" ] && exit 0

printf '\033[38;5;39m[SIEVE]\033[0m'

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

printf ' \033[38;5;39m\xf0\x9f\xaa\x99 %s\033[0m' "$HUMAN"
