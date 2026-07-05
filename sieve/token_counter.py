"""Rough token estimate. Not a real tokenizer — label all uses as estimates."""


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)
