# Sieve

Sieve is a terminal-native router for Claude Code.

Simple prompts go to a local Ollama model. Complex prompts go to real Claude
Code. Everything happens in your terminal — no dashboard, no browser, no
manual proxy configuration.

```bash
git clone <repo>
cd sieve
./install.sh
sieve doctor
sieve on
claude "what test framework does this repo use?"
sieve ledger
sieve off
```

## How it works

`sieve on` finds your real `claude` binary and writes a small shell shim to
`~/.sieve/bin/claude`. Once `~/.sieve/bin` is ahead of the real Claude
directory on your `PATH`, running `claude ...` actually runs the shim, which
calls `sieve run claude "$@"`:

```
you type: claude "what test framework does this repo use?"
              │
              ▼
     ~/.sieve/bin/claude (shim)
              │
              ▼
        sieve run claude ...
              │
      ┌───────┴────────┐
      ▼                ▼
 classify prompt   (heuristic, deterministic)
      │
 ┌────┴─────┐
 ▼           ▼
simple     complex / ambiguous / no prompt
 │           │
 ▼           ▼
gather     real claude binary
minimal    (subprocess, original args,
context    inherited stdio — streams
 │         normally)
 ▼
Ollama /api/chat
 │
 ▼
print answer + footer, log to ledger
```

If Ollama is offline, the model says `INSUFFICIENT_CONTEXT`, or no local
context can be found, Sieve automatically falls back to real Claude Code
instead of guessing.

## Setup

```bash
./install.sh          # creates .venv, installs sieve, inits ledger, runs doctor
source .venv/bin/activate
sieve on
```

`sieve on` prints the exact `export PATH=...` line to run (and to add to your
shell profile) if `~/.sieve/bin` isn't already ahead of your real Claude
install on `PATH`.

## Claude Code statusline

`sieve on` also wires a `[SIEVE:<model>]` badge into Claude Code's own
terminal statusline (`~/.claude/settings.json`), chaining with any existing
`statusLine` command rather than replacing it. Shows whichever model
answered the most recent request, e.g. `[SIEVE:qwen2.5-coder:7b]` or
`[SIEVE:claude]`. Renders nothing if Sieve is disabled. Safe to run
repeatedly — idempotent, never duplicates the chain. Start a new Claude Code
session to pick up the change.

## Example output

Local route:

```text
This project uses Jest as the test framework.

────────────────────────────────────
Sieve route: Ollama Local
Reason: simple read-only task matched: 'test framework'
Claude quota preserved: ~18K tokens (estimated)
Latency: 0.8s
────────────────────────────────────
```

Claude pass-through:

```text
[real Claude Code output streams normally]

────────────────────────────────────
Sieve route: Claude
Reason: complex-task keyword matched: 'refactor'
Claude quota used: estimated (see Claude Code's own usage UI)
Latency: 9.6s
────────────────────────────────────
```

## Commands

```text
sieve doctor    check Python, config, shim, PATH order, Ollama, ledger
sieve on        install the shim, detect real Claude
sieve off       remove the shim
sieve status    show enabled/disabled, shim path, real Claude, Ollama, mode
sieve run claude [args...]   what the shim actually calls — not for direct use
sieve ledger    5-hour routing summary (requests, local/claude split, quota preserved)
sieve history   recent request table
sieve config    print effective config (file + env overrides)
sieve reset     disable + reset config to defaults (ledger untouched)
```

## Config

`~/.sieve/config.json`:

```json
{
  "real_claude_path": "/usr/local/bin/claude",
  "shim_path": "/Users/name/.sieve/bin/claude",
  "enabled": true,
  "ollama_base_url": "http://localhost:11434",
  "ollama_model": "qwen2.5-coder:7b",
  "mode": "auto"
}
```

Env var overrides (see `.env.example`):

```env
SIEVE_MODE=auto              # auto | local_only | claude_only
SIEVE_OLLAMA_BASE_URL=http://localhost:11434
SIEVE_OLLAMA_MODEL=qwen2.5-coder:7b
SIEVE_MAX_CONTEXT_CHARS=20000
SIEVE_DEBUG=0                 # 1 for verbose routing logs
```

## Routing

See [docs/routing.md](docs/routing.md) for the full keyword ruleset. Short
version: package.json/README/test-framework/dependency/typo/format-style
questions go local; refactor/architecture/auth/security/migration/deploy/
multi-file/ambiguous/interactive-flag requests go to Claude. Anything that
doesn't clearly match either list also goes to Claude — the classifier is
conservative on purpose.

Two triage methods: `SIEVE_TRIAGE_METHOD=heuristic` (default, above) or
`llm` (asks the local Ollama model to decide, falling back to the heuristic
on any failure). See [docs/routing.md](docs/routing.md).

## Safety

Sieve never modifies your real Claude binary.
Sieve never steals or replays Claude auth tokens.
Sieve does not bypass usage limits — it only avoids sending requests to
Claude that don't need to go there.
Sieve only creates a PATH shim, removable at any time with `sieve off`.
The real Claude Code binary is called as an ordinary subprocess with your
original arguments; Sieve never touches its authentication.

"Quota preserved" and "quota used" are rough estimates
(`len(text) // 4` token approximation), not values read from Anthropic's own
usage accounting. Treat Claude Code's own `/status` and usage UI as the
source of truth.

## Tests

```bash
source .venv/bin/activate
pytest -q
```

## Docs

- [docs/architecture.md](docs/architecture.md)
- [docs/routing.md](docs/routing.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
