<div align="center">

<img src="docs/images/logo.png" alt="Sieve — terminal router for Claude Code" width="480">

**Terminal router for Claude Code.**

Simple prompts go local (Ollama) — zero Claude quota.
Complex prompts go to real Claude, untouched.

No dashboard. No browser. No manual config.

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![Tests](https://img.shields.io/badge/tests-52%20passing-brightgreen)

<img src="docs/images/statusline.png" alt="Sieve statusline badge showing which model answered the last prompt" width="480">

</div>

---

## ⚡ Quickstart

```bash
git clone https://github.com/Aditya-k24/sieve.git && cd sieve
./install.sh
sieve on
claude "what test framework does this repo use?"
```

That's it. `sieve on` once — works in every shell from then on.

## 🧰 What you get

| Command | What it does |
|---|---|
| `sieve on` / `off` | Install/remove the shim. Wires PATH + statusline automatically. |
| `sieve doctor` | One-shot health check — Ollama, shim, PATH, ledger. |
| `sieve status` | Current state at a glance. |
| `sieve ledger` / `history` | Quota preserved (est.) and recent request log. |
| `[SIEVE:<model>]` | Claude Code statusline badge — whichever model answered last. |
| `/sieve-status`, `/sieve-history`, ... | Same, as Claude Code slash commands. No terminal needed. |

## 🔀 How it works

```
claude "<prompt>"
       │
       ▼
~/.sieve/bin/claude  (shim)
       │
       ▼
   classifier ──── simple, read-only ────▶  Ollama (local, free)
       │                                        │
       └── complex / ambiguous / failed ◀───────┘
       ▼
 real Claude Code  (same binary, same args, same auth)
```

`sieve on` shims `claude` to route through a classifier first. Simple,
narrow, read-only prompts (package.json, README, "fix this typo", ...)
answer locally via Ollama. Anything complex, ambiguous, or that fails
locally falls straight through to real Claude — untouched.

Full breakdown: [docs/architecture.md](docs/architecture.md) · [docs/routing.md](docs/routing.md)

## 🛡️ Safety

- Never modifies your real Claude binary.
- Never touches Claude auth — the real binary runs as a plain subprocess.
- Doesn't bypass usage limits, just avoids sending Claude requests that
  don't need to go there.
- One PATH shim, removable anytime with `sieve off` — and if sieve itself
  is ever deleted, the shim falls through to the real `claude` on its own.
- Every failure path (corrupt config, Ollama down, broken stream, locked
  ledger) degrades to "plain Claude still works."

> "Quota preserved" is an estimate (`len // 4`), not Anthropic's own
> accounting — treat Claude Code's own usage UI as the source of truth.

## ⚙️ Config

Env vars override `~/.sieve/config.json` — see [.env.example](.env.example).
`SIEVE_TRIAGE_METHOD=llm` swaps the keyword classifier for local-LLM triage,
which also picks a Claude model tier (haiku/sonnet/opus) per request.

## 🧪 Tests

```bash
source .venv/bin/activate && pytest -q
```

## 📚 Docs

[architecture](docs/architecture.md) ·
[routing](docs/routing.md) ·
[troubleshooting](docs/troubleshooting.md)

---

<div align="center">

MIT © [Aditya Kulkarni](https://github.com/Aditya-k24)

</div>
