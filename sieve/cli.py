from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import typer

from sieve import __version__, classifier, context, doctor, ledger, ollama, shim, statusline, terminal
from sieve.claude_runner import run_claude
from sieve.config import (
    BIN_DIR,
    SIEVE_HOME,
    SieveConfig,
    load_config,
    save_config,
)
from sieve.token_counter import estimate_tokens

app = typer.Typer(help="Sieve — terminal-native router for Claude Code.")


def _version_callback(value: bool) -> None:
    if value:
        terminal.console.print(f"sieve {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Print version and exit."
    ),
) -> None:
    pass


# Claude Code flags that consume the next argument — their values must not be
# mistaken for the prompt (e.g. `claude --model opus` has no prompt).
VALUE_FLAGS = {
    "--model",
    "--add-dir",
    "--settings",
    "--permission-mode",
    "--mcp-config",
    "--session-id",
    "--append-system-prompt",
    "--allowedTools",
    "--disallowedTools",
    "--output-format",
    "--input-format",
    "--max-turns",
    "--fallback-model",
    "-r",
    "--resume",
}


def _user_model(args: list[str]) -> Optional[str]:
    """The value of a user-passed --model flag, if any."""
    for i, a in enumerate(args):
        if a == "--model" and i + 1 < len(args):
            return args[i + 1]
        if a.startswith("--model="):
            return a.split("=", 1)[1]
    return None


def _extract_prompt(args: list[str]) -> Optional[str]:
    """Heuristic: the prompt is the last positional argument that isn't a flag
    or a value consumed by a known value-taking flag."""
    prompt: Optional[str] = None
    skip_next = False
    for a in args:
        if skip_next:
            skip_next = False
            continue
        if a.startswith("-"):
            skip_next = a in VALUE_FLAGS
            continue
        prompt = a
    return prompt


@app.command(name="doctor")
def doctor_command() -> None:
    """Run environment/health checks."""
    cfg = load_config()
    results = doctor.run_checks(cfg)
    terminal.print_doctor_results(results)


@app.command(name="on")
def on_command() -> None:
    """Enable Sieve: discover real Claude, install the shim."""
    cfg = load_config()
    real_claude = shim.find_real_claude()
    if real_claude is None:
        terminal.console.print(
            "[red]No real 'claude' binary found in PATH.[/red] Install Claude Code first."
        )
        raise typer.Exit(code=1)

    cfg.real_claude_path = real_claude
    cfg.enabled = True
    save_config(cfg)
    shim.write_shim(real_claude)

    terminal.console.print(f"[green]Sieve enabled.[/green] Real Claude: {real_claude}")
    terminal.console.print(f"Shim installed at: {shim.SHIM_PATH}")

    if not shim.path_order_correct():
        rc_path = shim.default_shell_rc()
        added = shim.persist_path(rc_path)
        if added:
            terminal.console.print(
                f"\n[yellow]Added Sieve's shim to PATH in {rc_path}.[/yellow]\n"
                f"Open a new terminal, or run: source {rc_path}"
            )
        else:
            terminal.console.print(
                f"\n[yellow]PATH entry already in {rc_path} but not active in this shell yet.[/yellow]\n"
                f"Run: source {rc_path}"
            )
        terminal.console.print(
            f'For this exact shell right now: export PATH="{BIN_DIR}:$PATH"'
        )

    try:
        outcome = statusline.install()
        terminal.console.print(f"Claude Code statusline: {outcome}.")
    except (OSError, ValueError) as exc:
        terminal.console.print(
            f"[yellow]Skipped statusline setup ({exc}).[/yellow] Not required — sieve still works."
        )


@app.command(name="off")
def off_command() -> None:
    """Disable Sieve: remove the shim."""
    cfg = load_config()
    removed = shim.remove_shim()
    cfg.enabled = False
    save_config(cfg)
    if removed:
        terminal.console.print("[green]Sieve disabled.[/green] Shim removed.")
    else:
        terminal.console.print("Sieve disabled. (Shim was not installed.)")


@app.command(name="status")
def status_command() -> None:
    """Show current Sieve state."""
    cfg = load_config()
    online = ollama.is_online(cfg.ollama_base_url)
    terminal.console.print(f"Sieve: {'enabled' if cfg.enabled else 'disabled'}")
    terminal.console.print(f"Shim path: {shim.SHIM_PATH}")
    terminal.console.print(f"Real Claude: {cfg.real_claude_path or 'not detected'}")
    terminal.console.print(f"Ollama: {'online' if online else 'offline'}")
    terminal.console.print(f"Model: {cfg.ollama_model}")
    terminal.console.print(f"Ledger: {SIEVE_HOME / 'sieve.db'}")
    terminal.console.print(f"Mode: {cfg.mode}")
    triage_desc = cfg.triage_method
    if cfg.triage_method == "llm":
        triage_desc += f" ({cfg.triage_model or cfg.ollama_model})"
    terminal.console.print(f"Triage: {triage_desc}")


@app.command(name="ledger")
def ledger_command() -> None:
    """Show the last 5-hour routing summary."""
    summary = ledger.get_summary(hours=5.0)
    terminal.print_ledger_summary(summary)


@app.command(name="history")
def history_command(limit: int = typer.Option(20, help="Rows to show")) -> None:
    """Show recent request history."""
    rows = ledger.get_history(limit=limit)
    terminal.print_history_table(rows)


@app.command(name="config")
def config_command() -> None:
    """Print the effective config (file + env overrides)."""
    cfg = load_config()
    terminal.console.print(cfg.model_dump_json(indent=2))


@app.command(name="reset")
def reset_command() -> None:
    """Disable Sieve and reset config to defaults. Does not touch the ledger."""
    shim.remove_shim()
    save_config(SieveConfig())
    terminal.console.print("Sieve reset: shim removed, config restored to defaults.")


@app.command(
    name="run",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def run_command(
    ctx: typer.Context,
    target: str = typer.Argument("claude", help="Target binary the shim invokes"),
) -> None:
    """Entry point the shim calls: `sieve run claude [args...]`."""
    args = ctx.args
    cfg = load_config()
    cwd = Path.cwd()

    if target != "claude":
        terminal.console.print(f"[red]Unknown run target: {target}[/red]")
        raise typer.Exit(code=1)

    if not cfg.real_claude_path:
        terminal.console.print(
            "[red]Sieve has no real Claude binary configured.[/red] Run 'sieve on' first."
        )
        raise typer.Exit(code=1)

    if not cfg.enabled:
        # Shim can outlive `sieve off` (shared dotfiles, stale PATH copy) —
        # a disabled Sieve must behave exactly like plain claude: no routing,
        # no footer, no ledger row.
        result = run_claude(cfg.real_claude_path, args)
        raise typer.Exit(code=result.exit_code)

    prompt = _extract_prompt(args)

    if cfg.mode == "claude_only":
        decision = classifier.RouteDecision(
            route="claude", complexity=5, confidence=1.0, reason="SIEVE_MODE=claude_only", context_mode="full_claude"
        )
    elif cfg.mode == "local_only":
        decision = classifier.RouteDecision(
            route="local", complexity=1, confidence=1.0, reason="SIEVE_MODE=local_only", context_mode="selected_files"
        )
    else:
        decision = classifier.classify_auto(prompt, args, cfg)

    terminal.debug(f"classification: {decision}")

    if decision.route == "local" and prompt:
        _run_local_route(cfg, prompt, args, decision, cwd)
    else:
        _run_claude_route(cfg, prompt, args, decision)


def _fallback_decision(decision, reason: str) -> "classifier.RouteDecision":
    """Reroute a failed local attempt to Claude, keeping the original scoring."""
    terminal.debug(f"{reason} — rerouting to Claude")
    return classifier.RouteDecision(
        route="claude",
        complexity=decision.complexity,
        confidence=decision.confidence,
        reason=reason,
        context_mode="full_claude",
    )


def _log_request(record: ledger.RequestRecord) -> None:
    """Ledger writes are best-effort: a locked/corrupt/unwritable DB must never
    eat the answer or the exit code."""
    try:
        ledger.insert_request(record)
    except Exception as exc:  # noqa: BLE001 — any sqlite/OS failure is non-fatal here
        terminal.debug(f"ledger write failed (non-fatal): {exc}")


def _run_local_route(cfg: SieveConfig, prompt: str, args: list[str], decision, cwd: Path) -> None:
    ctx_text = context.gather_context(prompt, cwd, cfg.max_context_chars)
    if ctx_text is None:
        _run_claude_route(cfg, prompt, args, _fallback_decision(decision, "no local context available"))
        return

    if not ollama.is_online(cfg.ollama_base_url):
        _run_claude_route(cfg, prompt, args, _fallback_decision(decision, "ollama offline"))
        return

    user_content = f"Context:\n{ctx_text}\n\nQuestion: {prompt}"
    start = time.monotonic()
    try:
        answer = ollama.chat(cfg.ollama_base_url, cfg.ollama_model, user_content)
    except ollama.OllamaError:
        _run_claude_route(cfg, prompt, args, _fallback_decision(decision, "ollama request failed"))
        return
    latency_s = time.monotonic() - start

    if ollama.INSUFFICIENT_MARKER in answer:
        _run_claude_route(
            cfg, prompt, args, _fallback_decision(decision, "local model reported insufficient context")
        )
        return

    input_tokens = estimate_tokens(user_content)
    output_tokens = estimate_tokens(answer)
    quota_saved = input_tokens + output_tokens

    # Log before printing: if stdout closes early (piped into `head`, Ctrl-C,
    # a broken pipe) the print can raise, but the request still gets recorded.
    _log_request(
        ledger.RequestRecord(
            command=" ".join(args),
            route="local",
            model=cfg.ollama_model,
            complexity=decision.complexity,
            confidence=decision.confidence,
            reason=decision.reason,
            context_mode=decision.context_mode,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_quota_saved=quota_saved,
            latency_ms=int(latency_s * 1000),
            success=True,
        )
    )

    terminal.console.print(answer)
    terminal.print_footer(
        route="local",
        reason=decision.reason,
        quota_line=f"[bold]Claude quota preserved:[/bold] {terminal.format_tokens(quota_saved)} (estimated)",
        latency_s=latency_s,
    )


def _run_claude_route(cfg: SieveConfig, prompt: Optional[str], args: list[str], decision) -> None:
    result = run_claude(cfg.real_claude_path, args, model_override=decision.claude_model)
    input_tokens = estimate_tokens(prompt) if prompt else 0
    # User's --model wins inside run_claude, so it must win in the label too;
    # triage's pick applies only when the user didn't choose. Bare "claude"
    # means Claude Code used its own default, which Sieve can't observe.
    model_label = _user_model(args) or decision.claude_model or "claude"

    # Log before printing — same reasoning as the local route above.
    _log_request(
        ledger.RequestRecord(
            command=" ".join(args),
            route="claude",
            model=model_label,
            complexity=decision.complexity,
            confidence=decision.confidence,
            reason=decision.reason,
            context_mode=decision.context_mode,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=0,
            estimated_quota_saved=0,
            latency_ms=result.latency_ms,
            success=result.exit_code == 0,
            error_message=None if result.exit_code == 0 else f"exit code {result.exit_code}",
        )
    )

    terminal.print_footer(
        route="claude",
        reason=decision.reason,
        quota_line="[bold]Claude quota used:[/bold] estimated (see Claude Code's own usage UI)",
        latency_s=result.latency_ms / 1000,
    )

    raise typer.Exit(code=result.exit_code)


if __name__ == "__main__":
    app()
