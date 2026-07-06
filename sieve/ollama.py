"""Thin client for Ollama's /api/chat and /api/tags."""

from __future__ import annotations

import json

import httpx

SYSTEM_PROMPT = (
    "You are Sieve Local. Answer concise developer questions using only provided "
    "context. If context is insufficient, say INSUFFICIENT_CONTEXT."
)

INSUFFICIENT_MARKER = "INSUFFICIENT_CONTEXT"


class OllamaError(Exception):
    """Ollama unreachable or returned an unusable response."""


def is_online(base_url: str, timeout: float = 2.0) -> bool:
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def model_available(base_url: str, model: str, timeout: float = 2.0) -> bool:
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
        r.raise_for_status()
        names = {m.get("name") for m in r.json().get("models", [])}
        return model in names
    except httpx.HTTPError:
        return False


def chat(base_url: str, model: str, user_content: str, timeout: float = 60.0) -> str:
    """Streams the response from Ollama and returns the full assembled text.
    Buffered rather than printed incrementally so a trailing INSUFFICIENT_CONTEXT
    can still cleanly reroute to Claude instead of half-printing a wrong answer."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "stream": True,
    }
    chunks: list[str] = []
    try:
        with httpx.stream(
            "POST", f"{base_url.rstrip('/')}/api/chat", json=payload, timeout=timeout
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                content = data.get("message", {}).get("content", "")
                if content:
                    chunks.append(content)
                if data.get("done"):
                    break
    except httpx.HTTPError as exc:
        raise OllamaError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise OllamaError(f"malformed stream line from ollama: {exc}") from exc

    return "".join(chunks)


def triage(base_url: str, model: str, system_prompt: str, user_prompt: str, timeout: float = 15.0) -> str:
    """Single-shot, non-streaming, JSON-mode call — used for LLM-based routing
    triage rather than answering a question directly. Kept short-timeout since
    a slow triage call defeats the point of routing cheaply."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
    }
    try:
        response = httpx.post(f"{base_url.rstrip('/')}/api/chat", json=payload, timeout=timeout)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise OllamaError(str(exc)) from exc

    try:
        return response.json()["message"]["content"]
    except (KeyError, ValueError) as exc:
        raise OllamaError(f"unexpected ollama response shape: {exc}") from exc
