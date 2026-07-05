# Routing

`sieve/classifier.py` is a deterministic keyword matcher — no LLM triage in
v1. Order of checks in `classify(prompt, raw_args)`:

1. **No prompt** → Claude (`reason: "no prompt detected"`, confidence 1.0).
2. **Interactive/session flag** (`-c`, `--continue`, `-r`, `--resume`, `-i`,
   `--interactive`) present in args → Claude. Sieve can't safely reconstruct
   resumed/interactive session state locally.
3. **Complex-task keyword** anywhere in the prompt → Claude, confidence 0.95:
   `refactor`, `implement`, `architecture`, `auth`, `security`, `migration`,
   `migrate`, `deploy`, `production`, `failing test(s)`, `multi-file`,
   `multiple files`, `across files`, `across the codebase`.
4. **Simple read-only keyword** → local, confidence 0.85:
   `package.json`, `test framework`, `what tests`, `summarize/summarise
   readme`, `readme`, `list dependencies`, `dependencies`, `explain this
   file`, `what does this file`, `what does this function`, `format this
   text`, `fix typo`, `fix this typo`.
5. **Neither list matches** → Claude, confidence 0.4 (`"ambiguous prompt, no
   confident keyword match"`). Confidence is below
   `CONFIDENCE_THRESHOLD = 0.6`, so anything ambiguous conservatively falls
   through to Claude rather than guessing locally.

Complex-task keywords are checked before simple ones, so e.g. "refactor how
package.json scripts work" routes to Claude, not local.

## Context modes

Each local-route match also carries a `context_mode`:

- `selected_files` — needs to read specific files (package.json, README,
  manifest files, an explicitly named file).
- `prompt_only` — needs nothing but the prompt itself (format text, fix a
  typo).
- `full_claude` — always paired with `route: claude`.

## Safety nets after classification

Even a "local" decision can still reroute to Claude at runtime:

- `context.gather_context()` returns `None` → no local context available.
- `ollama.is_online()` is `False` → Ollama offline.
- The Ollama request raises `OllamaError` (timeout, connection refused).
- The model's reply contains `INSUFFICIENT_CONTEXT`.

Every reroute is logged with its own `reason` in the ledger, distinct from
the original classification reason.

## Modes

`SIEVE_MODE` / `config.json["mode"]`:

- `auto` (default) — run the classifier above.
- `local_only` — force `route: local` for every request (still subject to
  the runtime safety nets above).
- `claude_only` — force `route: claude` for every request, unconditionally.

## Extending the ruleset

Add keywords to `LOCAL_KEYWORDS` / `CLAUDE_KEYWORDS` in `classifier.py`.
Order matters: `CLAUDE_KEYWORDS` is checked first, so anything that should
always win over a simple-sounding phrase belongs there.
