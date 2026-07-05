"""Minimal local context gathering for the Ollama route.
Never dumps a whole repo — only the specific files a prompt implies."""

from __future__ import annotations

import re
from pathlib import Path

MANIFEST_FILES = [
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "pytest.ini",
    "pom.xml",
    "build.gradle",
    "Cargo.toml",
    "go.mod",
]

_FILE_TOKEN_RE = re.compile(r"[\w./-]+\.[A-Za-z0-9]{1,6}")


def _read(path: Path, budget: int) -> str | None:
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return None
    return text[:budget]


def _find_explicit_file(prompt: str, cwd: Path) -> Path | None:
    for token in _FILE_TOKEN_RE.findall(prompt):
        candidate = (cwd / token).resolve()
        if candidate.is_file() and cwd.resolve() in candidate.parents:
            return candidate
    return None


def gather_context(prompt: str, cwd: Path, max_chars: int = 20000) -> str | None:
    """Returns combined context text, or None if nothing relevant was found
    or the only relevant file is too large to answer from safely."""
    lower = prompt.lower()
    parts: list[str] = []
    remaining = max_chars

    def add(label: str, path: Path) -> None:
        nonlocal remaining
        if remaining <= 0:
            return
        content = _read(path, remaining)
        if content is None:
            return
        parts.append(f"# {label}\n{content}")
        remaining -= len(content)

    if "package.json" in lower:
        p = cwd / "package.json"
        if p.is_file():
            add("package.json", p)

    if "test framework" in lower or "what tests" in lower or "dependenc" in lower:
        for name in MANIFEST_FILES:
            p = cwd / name
            if p.is_file():
                add(name, p)

    if "readme" in lower or "summarize" in lower or "summarise" in lower:
        for candidate in ("README.md", "README", "readme.md"):
            p = cwd / candidate
            if p.is_file():
                add(candidate, p)
                break

    if "this file" in lower or "this function" in lower:
        explicit = _find_explicit_file(prompt, cwd)
        if explicit is not None:
            full = explicit.read_text(errors="replace")
            if len(full) > max_chars:
                # A single huge file can't be answered from safely on the local
                # route — better to fall through to Claude than guess from a cut.
                return None
            add(str(explicit.relative_to(cwd)), explicit)

    if not parts:
        return None

    combined = "\n\n".join(parts)
    return combined[:max_chars]
