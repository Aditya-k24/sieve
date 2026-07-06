from sieve.cli import _extract_prompt


def test_extract_prompt_plain():
    assert _extract_prompt(["what test framework does this repo use?"]) == (
        "what test framework does this repo use?"
    )


def test_extract_prompt_empty():
    assert _extract_prompt([]) is None


def test_extract_prompt_ignores_flag_values():
    # `claude --model opus` has no prompt — "opus" is the flag's value.
    assert _extract_prompt(["--model", "opus"]) is None


def test_extract_prompt_after_value_flag():
    assert _extract_prompt(["--model", "opus", "fix typo"]) == "fix typo"


def test_extract_prompt_with_print_flag():
    assert _extract_prompt(["-p", "summarize readme"]) == "summarize readme"


def test_extract_prompt_takes_last_positional():
    assert _extract_prompt(["--add-dir", "/tmp", "explain this file"]) == "explain this file"
