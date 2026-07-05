from sieve.token_counter import estimate_tokens


def test_estimate_tokens_basic():
    assert estimate_tokens("a" * 40) == 10


def test_estimate_tokens_minimum_one():
    assert estimate_tokens("") == 1
    assert estimate_tokens("a") == 1
