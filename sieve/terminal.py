"""Rich terminal output. Minimal by default; SIEVE_DEBUG=1 for verbose logs."""

from __future__ import annotations

import os

from rich.console import Console
from rich.table import Table

console = Console()


def debug_enabled() -> bool:
    return os.environ.get("SIEVE_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}


def debug(msg: str) -> None:
    if debug_enabled():
        console.print(f"[dim][sieve debug][/dim] {msg}")


def print_footer(route: str, reason: str, quota_line: str, latency_s: float) -> None:
    bar = "─" * 36
    route_label = "Ollama Local" if route == "local" else "Claude"
    console.print(f"\n{bar}")
    console.print(f"[bold]Sieve route:[/bold] {route_label}")
    console.print(f"[bold]Reason:[/bold] {reason}")
    console.print(quota_line)
    console.print(f"[bold]Latency:[/bold] {latency_s:.1f}s")
    console.print(bar)


def format_tokens(n: int) -> str:
    if n >= 1000:
        return f"~{n / 1000:.0f}K tokens" if n >= 10000 else f"~{n / 1000:.1f}K tokens"
    return f"~{n} tokens"


def print_ledger_summary(summary: dict) -> None:
    console.print(f"Requests: {summary['requests']}")
    console.print(f"Local: {summary['local']}")
    console.print(f"Claude: {summary['claude']}")
    console.print(f"Quota preserved: {format_tokens(summary['quota_preserved_tokens'])} (estimated)")
    console.print(f"Route efficiency: {summary['route_efficiency_local_pct']:.1f}% local")
    console.print(f"Average latency: {summary['avg_latency_s']:.1f}s")


def print_history_table(rows: list[dict]) -> None:
    table = Table(title="Sieve request history")
    table.add_column("Time")
    table.add_column("Route")
    table.add_column("Model")
    table.add_column("Reason", overflow="fold")
    table.add_column("Conf.")
    table.add_column("Quota saved")
    table.add_column("Latency")
    table.add_column("OK")

    for r in rows:
        table.add_row(
            r["timestamp"].split("T")[1].split(".")[0] if "T" in r["timestamp"] else r["timestamp"],
            r["route"],
            r["model"] or "-",
            r["reason"] or "",
            f"{r['confidence']:.2f}" if r["confidence"] is not None else "-",
            format_tokens(r["estimated_quota_saved"] or 0),
            f"{(r['latency_ms'] or 0) / 1000:.1f}s",
            "✔" if r["success"] else "✘",
        )
    console.print(table)


def print_doctor_results(results: list[tuple[str, bool, str]]) -> None:
    table = Table(title="Sieve doctor")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail", overflow="fold")
    for name, ok, detail in results:
        table.add_row(name, "[green]OK[/green]" if ok else "[red]FAIL[/red]", detail)
    console.print(table)
