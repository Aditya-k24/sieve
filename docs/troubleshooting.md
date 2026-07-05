# Troubleshooting

## `claude` still runs the real binary, not Sieve

Run `sieve doctor` and check "PATH order". If it fails:

```bash
export PATH="$HOME/.sieve/bin:$PATH"
```

Add that line to your shell profile (`~/.zshrc` or `~/.bashrc`) to make it
permanent, then open a new shell.

## `sieve on` says "No real 'claude' binary found in PATH"

Sieve searches every `PATH` directory except `~/.sieve/bin` for an executable
named `claude`. Install Claude Code first, confirm `claude --version` works
in a plain shell, then re-run `sieve on`.

## Every request goes to Claude, even simple ones

Check `sieve doctor`:

- **Ollama reachable: FAIL** — start Ollama (`ollama serve`) or check
  `SIEVE_OLLAMA_BASE_URL` / `ollama_base_url` in `~/.sieve/config.json`.
- **Ollama model available: FAIL** — `ollama pull <model>` for the model
  named in `sieve status`.
- Also check `sieve history` — the `reason` column shows exactly why a
  request rerouted (`ollama offline`, `no local context available`, `local
  model reported insufficient context`, etc.).
- If the prompt didn't match any keyword in `docs/routing.md`, that's
  expected — ambiguous prompts intentionally fall through to Claude.

## `sieve run claude ...` fails with "no real Claude binary configured"

Run `sieve on` first — it's what stores `real_claude_path` in
`~/.sieve/config.json`.

## `sieve` fails with `ModuleNotFoundError: No module named 'sieve'`

`install.sh` uses a regular (non-editable) `pip install .` specifically to
avoid this: some Python builds don't reliably process `.pth`
editable-install redirects (seen intermittently even with plain
`python3 -m venv`, and consistently with `uv`-managed venvs, which skip full
site initialization for speed). If you installed with `pip install -e .` and
hit this, reinstall with `pip install .` instead. Re-run after any source
change if you do use editable mode for development.

## Uninstalling

```bash
sieve off      # removes ~/.sieve/bin/claude
sieve reset    # also resets ~/.sieve/config.json to defaults
rm -rf ~/.sieve   # full removal, including the ledger
```

Sieve never modifies the real Claude binary, so removing the shim (or the
whole `~/.sieve` directory) fully restores normal `claude` behavior.
