from sieve import ollama
from sieve.classifier import TriageError, classify, classify_auto, classify_llm
from sieve.config import SieveConfig


def test_local_route_package_json():
    d = classify("what scripts are in package.json?")
    assert d.route == "local"
    assert d.context_mode == "selected_files"


def test_local_route_test_framework():
    d = classify("what test framework does this repo use?")
    assert d.route == "local"


def test_local_route_fix_typo():
    d = classify("fix typo in this sentence")
    assert d.route == "local"
    assert d.context_mode == "prompt_only"


def test_claude_route_refactor():
    d = classify("refactor the auth module to use the new session store")
    assert d.route == "claude"
    assert d.confidence >= 0.9


def test_claude_route_multi_file():
    d = classify("implement this feature across multiple files")
    assert d.route == "claude"


def test_claude_route_security():
    d = classify("review this for security issues in the login flow")
    assert d.route == "claude"


def test_no_prompt_routes_claude():
    d = classify(None)
    assert d.route == "claude"
    assert d.reason == "no prompt detected"


def test_interactive_flag_routes_claude():
    d = classify("what does this do", raw_args=["--continue", "what does this do"])
    assert d.route == "claude"
    assert "flag" in d.reason


def test_ambiguous_low_confidence_routes_claude():
    d = classify("hello there")
    assert d.route == "claude"
    assert d.confidence < 0.6


def test_classify_llm_parses_valid_response(monkeypatch):
    valid_json = (
        '{"route": "local", "complexity": 2, "confidence": 0.9, '
        '"reason": "manifest read", "context_mode": "selected_files"}'
    )
    monkeypatch.setattr(ollama, "triage", lambda *a, **kw: valid_json)

    d = classify_llm("what's in package.json?", [], "http://localhost:11434", "qwen2.5-coder:7b")
    assert d.route == "local"
    assert d.confidence == 0.9


def test_classify_llm_skips_call_on_precheck(monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("should not call ollama.triage when precheck short-circuits")

    monkeypatch.setattr(ollama, "triage", boom)

    d = classify_llm(None, [], "http://localhost:11434", "qwen2.5-coder:7b")
    assert d.route == "claude"
    assert d.reason == "no prompt detected"


def test_classify_llm_raises_on_malformed_json(monkeypatch):
    monkeypatch.setattr(ollama, "triage", lambda *a, **kw: "not json")

    try:
        classify_llm("what's in package.json?", [], "http://localhost:11434", "qwen2.5-coder:7b")
        assert False, "expected TriageError"
    except TriageError:
        pass


def test_classify_llm_raises_on_ollama_offline(monkeypatch):
    def raise_offline(*a, **kw):
        raise ollama.OllamaError("connection refused")

    monkeypatch.setattr(ollama, "triage", raise_offline)

    try:
        classify_llm("what's in package.json?", [], "http://localhost:11434", "qwen2.5-coder:7b")
        assert False, "expected TriageError"
    except TriageError:
        pass


def test_classify_auto_uses_heuristic_by_default():
    cfg = SieveConfig(triage_method="heuristic")
    d = classify_auto("fix typo in this sentence", [], cfg)
    assert d.route == "local"


def test_classify_auto_falls_back_to_heuristic_on_triage_failure(monkeypatch):
    def raise_offline(*a, **kw):
        raise ollama.OllamaError("connection refused")

    monkeypatch.setattr(ollama, "triage", raise_offline)

    cfg = SieveConfig(triage_method="llm", ollama_model="qwen2.5-coder:7b")
    d = classify_auto("fix typo in this sentence", [], cfg)
    assert d.route == "local"  # heuristic fallback still matches
