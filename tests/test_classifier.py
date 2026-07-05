from sieve.classifier import classify


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
