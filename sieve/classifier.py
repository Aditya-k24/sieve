"""Deterministic heuristic router. No LLM triage yet — keyword rules only.
Conservative by design: anything ambiguous or unmatched falls through to Claude."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

# Flags that imply an interactive/stateful Claude Code session Sieve can't safely
# reconstruct locally (resuming history, continuing a conversation, REPL mode).
INTERACTIVE_FLAGS = {"-c", "--continue", "-r", "--resume", "-i", "--interactive"}

CONFIDENCE_THRESHOLD = 0.6

# (keyword, context_mode) — first match wins, checked in list order.
LOCAL_KEYWORDS: list[tuple[str, str]] = [
    ("package.json", "selected_files"),
    ("test framework", "selected_files"),
    ("what tests", "selected_files"),
    ("summarize readme", "selected_files"),
    ("summarise readme", "selected_files"),
    ("readme", "selected_files"),
    ("list dependencies", "selected_files"),
    ("dependencies", "selected_files"),
    ("explain this file", "selected_files"),
    ("what does this file", "selected_files"),
    ("what does this function", "selected_files"),
    ("format this text", "prompt_only"),
    ("fix typo", "prompt_only"),
    ("fix this typo", "prompt_only"),
]

CLAUDE_KEYWORDS: list[str] = [
    "refactor",
    "implement",
    "architecture",
    "auth",
    "security",
    "migration",
    "migrate",
    "deploy",
    "production",
    "failing test",
    "failing tests",
    "multi-file",
    "multiple files",
    "across files",
    "across the codebase",
]


class RouteDecision(BaseModel):
    route: Literal["local", "claude"]
    complexity: int
    confidence: float
    reason: str
    context_mode: Literal["prompt_only", "selected_files", "full_claude"]


def _has_interactive_flag(raw_args: list[str]) -> bool:
    return any(a in INTERACTIVE_FLAGS for a in raw_args)


def classify(prompt: str | None, raw_args: list[str] | None = None) -> RouteDecision:
    raw_args = raw_args or []

    if not prompt or not prompt.strip():
        return RouteDecision(
            route="claude",
            complexity=5,
            confidence=1.0,
            reason="no prompt detected",
            context_mode="full_claude",
        )

    if _has_interactive_flag(raw_args):
        return RouteDecision(
            route="claude",
            complexity=5,
            confidence=1.0,
            reason="interactive/session flag present",
            context_mode="full_claude",
        )

    lower = prompt.lower()

    for kw in CLAUDE_KEYWORDS:
        if kw in lower:
            return RouteDecision(
                route="claude",
                complexity=8,
                confidence=0.95,
                reason=f"complex-task keyword matched: '{kw}'",
                context_mode="full_claude",
            )

    for kw, context_mode in LOCAL_KEYWORDS:
        if kw in lower:
            return RouteDecision(
                route="local",
                complexity=2,
                confidence=0.85,
                reason=f"simple read-only task matched: '{kw}'",
                context_mode=context_mode,  # type: ignore[arg-type]
            )

    # Nothing matched either list — ambiguous. Below CONFIDENCE_THRESHOLD always
    # routes to Claude; the comparison is explicit so the threshold stays load-bearing.
    ambiguous_confidence = 0.4
    route: Literal["local", "claude"] = "claude" if ambiguous_confidence < CONFIDENCE_THRESHOLD else "local"
    return RouteDecision(
        route=route,
        complexity=5,
        confidence=ambiguous_confidence,
        reason="ambiguous prompt, no confident keyword match",
        context_mode="full_claude",
    )
