# Architecture

Sieve is a terminal shim, not a network proxy. There is no HTTP server, no
listening port, no browser step.

## Components

- **`sieve/shim.py`** — writes `~/.sieve/bin/claude`, a two-line bash script
  that execs `sieve run claude "$@"`. Also discovers the real `claude`
  binary by searching `PATH`, explicitly skipping `~/.sieve/bin` so it never
  detects its own shim as "real."
- **`sieve/cli.py`** — Typer app. `sieve run claude [args...]` is the command
  the shim actually calls; it extracts a prompt, classifies it, and either
  answers locally or execs the real Claude binary.
- **`sieve/classifier.py`** — deterministic keyword-based `classify()`.
  Returns a `RouteDecision` (route, complexity, confidence, reason,
  context_mode). No network call, no LLM triage in v1.
- **`sieve/context.py`** — gathers the minimal local context a simple prompt
  needs (package.json, README, manifest files, or an explicitly named file).
  Returns `None` if nothing relevant is found or the relevant file is too
  large — both cases fall through to Claude.
- **`sieve/ollama.py`** — thin client for Ollama's `/api/chat` and
  `/api/tags`. Buffers the streamed response so an `INSUFFICIENT_CONTEXT`
  reply can still cleanly reroute to Claude before anything is printed.
- **`sieve/claude_runner.py`** — runs the real Claude binary via
  `subprocess.run([real_claude_path, *args])` with inherited stdio. No
  header inspection, no auth handling — Claude Code's own login flow is
  untouched.
- **`sieve/ledger.py`** — SQLite (`~/.sieve/sieve.db`) request log and 5-hour
  rollup summary.
- **`sieve/config.py`** — `~/.sieve/config.json` + env var overrides.
- **`sieve/terminal.py`** — Rich console output: the route footer, doctor
  table, ledger summary, history table.

## Why a shim instead of a gateway

An HTTP gateway (`ANTHROPIC_BASE_URL`) requires the client to speak the
Anthropic Messages protocol correctly forever, including new headers/fields
Claude Code adds over time. A terminal shim only intercepts the CLI
invocation — Claude Code's own network behavior, auth, and protocol handling
are completely untouched whenever a request routes to Claude. That's a much
smaller compatibility surface to maintain.

## Request flow

1. User runs `claude "<prompt>"`.
2. Shell resolves `claude` to `~/.sieve/bin/claude` (requires that directory
   to be earlier on `PATH` than the real Claude install — `sieve doctor`
   checks this).
3. Shim execs `sieve run claude "$@"`.
4. `sieve run` extracts a prompt (last non-flag argument), classifies it.
5. **Local route**: gather context → call Ollama → if `INSUFFICIENT_CONTEXT`
   or any failure, reroute to Claude instead. Otherwise print the answer and
   a footer, log to the ledger.
6. **Claude route**: exec the real Claude binary with the original args,
   inherited stdio (so streaming/interactive behavior is identical to
   calling Claude directly). Log to the ledger, exit with Claude's exit code.
