"""Routing decisions. Two triage methods:

- classify(): deterministic keyword rules. Default. No network call.
- classify_llm(): asks the local Ollama model to triage instead. Falls back
  to classify() on any failure (offline, bad JSON, invalid schema).

Both are conservative by design: anything ambiguous, unmatched, or that fails
to parse falls through to Claude rather than guessing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

from sieve import ollama

if TYPE_CHECKING:
    from sieve.config import SieveConfig

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


class TriageError(Exception):
    """LLM triage produced no usable decision — caller should fall back to classify()."""


TRIAGE_SYSTEM_PROMPT = """You are Sieve's routing triage for a coding assistant CLI. Given a user's terminal prompt, decide whether it can be answered by a small local model with minimal file context ("local") or needs a frontier coding assistant ("claude").

Route "local" only for narrow, read-only, single-file/manifest questions: reading package.json/README/config, explaining a specific file or function, formatting text, fixing a typo, listing dependencies.

Route "claude" for anything involving refactoring, multi-file changes, architecture, security/auth, migrations, deployment, debugging failing tests, or anything ambiguous.

Respond with ONLY a JSON object, no prose, matching exactly this schema:
{"route": "local" or "claude", "complexity": integer 1-10, "confidence": float 0-1, "reason": short string, "context_mode": "prompt_only" or "selected_files" or "full_claude"}

If unsure, set route to "claude" and confidence below 0.6."""


def _has_interactive_flag(raw_args: list[str]) -> bool:
    return any(a in INTERACTIVE_FLAGS for a in raw_args)


def _precheck(prompt: str | None, raw_args: list[str]) -> RouteDecision | None:
    """Shared short-circuit for both classifiers — a missing prompt or an
    interactive/session flag is already a certain answer, so neither needs
    to waste an LLM call reaching it."""
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

    return None


def classify(prompt: str | None, raw_args: list[str] | None = None) -> RouteDecision:
    raw_args = raw_args or []

    precheck = _precheck(prompt, raw_args)
    if precheck is not None:
        return precheck

    assert prompt is not None
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


def classify_llm(
    prompt: str | None,
    raw_args: list[str] | None,
    base_url: str,
    model: str,
    timeout: float = 15.0,
) -> RouteDecision:
    """Asks the local Ollama model to make the routing decision instead of
    keyword rules. Raises TriageError on any failure — offline, malformed
    JSON, or a response that doesn't match RouteDecision — so the caller can
    fall back to classify() rather than route on garbage."""
    raw_args = raw_args or []

    precheck = _precheck(prompt, raw_args)
    if precheck is not None:
        return precheck

    assert prompt is not None
    try:
        content = ollama.triage(base_url, model, TRIAGE_SYSTEM_PROMPT, prompt, timeout=timeout)
        return RouteDecision.model_validate_json(content)
    except (ollama.OllamaError, ValueError) as exc:
        # ValueError covers both json.JSONDecodeError and pydantic's
        # ValidationError (a ValueError subclass) in one catch.
        raise TriageError(str(exc)) from exc


def classify_auto(prompt: str | None, raw_args: list[str] | None, cfg: "SieveConfig") -> RouteDecision:
    """Dispatches to LLM or heuristic triage per cfg.triage_method, falling
    back to the heuristic on any LLM failure. This is what SIEVE_MODE=auto
    actually calls — conservative either way, since classify() itself
    defaults ambiguous/failed cases to Claude."""
    raw_args = raw_args or []

    if cfg.triage_method == "llm":
        try:
            return classify_llm(prompt, raw_args, cfg.ollama_base_url, cfg.triage_model or cfg.ollama_model)
        except TriageError:
            pass

    return classify(prompt, raw_args)
