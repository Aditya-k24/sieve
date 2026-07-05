"""Runs the real Claude Code binary as a subprocess. Never touches auth."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass


@dataclass
class ClaudeResult:
    exit_code: int
    latency_ms: int


def run_claude(real_claude_path: str, args: list[str]) -> ClaudeResult:
    """Inherits the current stdio so Claude Code's own streaming/TTY behavior
    (colors, prompts, interactive input) works exactly as if called directly."""
    start = time.monotonic()
    proc = subprocess.run([real_claude_path, *args])
    latency_ms = int((time.monotonic() - start) * 1000)
    return ClaudeResult(exit_code=proc.returncode, latency_ms=latency_ms)
