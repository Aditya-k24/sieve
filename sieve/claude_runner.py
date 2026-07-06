"""Runs the real Claude Code binary as a subprocess. Never touches auth."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass


@dataclass
class ClaudeResult:
    exit_code: int
    latency_ms: int


def run_claude(real_claude_path: str, args: list[str], model_override: str | None = None) -> ClaudeResult:
    """Inherits the current stdio so Claude Code's own streaming/TTY behavior
    (colors, prompts, interactive input) works exactly as if called directly.

    model_override, when set, adds `--model <alias>` (e.g. "sonnet", "haiku",
    "opus") — but never if the user already passed their own --model, since
    explicit user intent always wins over triage's choice."""
    final_args = list(args)
    user_set_model = any(a == "--model" or a.startswith("--model=") for a in args)
    if model_override and not user_set_model:
        final_args = ["--model", model_override, *final_args]

    start = time.monotonic()
    proc = subprocess.run([real_claude_path, *final_args])
    latency_ms = int((time.monotonic() - start) * 1000)
    return ClaudeResult(exit_code=proc.returncode, latency_ms=latency_ms)
