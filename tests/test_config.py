import pytest

from sieve import config

SIEVE_ENV_VARS = [
    "SIEVE_MODE",
    "SIEVE_OLLAMA_BASE_URL",
    "SIEVE_OLLAMA_MODEL",
    "SIEVE_MAX_CONTEXT_CHARS",
    "SIEVE_DEBUG",
    "SIEVE_TRIAGE_METHOD",
    "SIEVE_TRIAGE_MODEL",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in SIEVE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")


def test_corrupt_config_file_falls_back_to_defaults(capsys):
    config.CONFIG_PATH.write_text("{this is not json")
    cfg = config.load_config()
    assert cfg.enabled is False
    assert cfg.mode == "auto"
    assert "corrupt config" in capsys.readouterr().err


def test_invalid_env_mode_is_ignored(monkeypatch, capsys):
    monkeypatch.setenv("SIEVE_MODE", "garbage")
    cfg = config.load_config()
    assert cfg.mode == "auto"
    assert "invalid SIEVE_" in capsys.readouterr().err


def test_invalid_env_max_context_chars_is_ignored(monkeypatch):
    monkeypatch.setenv("SIEVE_MAX_CONTEXT_CHARS", "not-a-number")
    cfg = config.load_config()
    assert cfg.max_context_chars == 20000


def test_valid_env_overrides_apply(monkeypatch):
    monkeypatch.setenv("SIEVE_MODE", "claude_only")
    monkeypatch.setenv("SIEVE_MAX_CONTEXT_CHARS", "5000")
    cfg = config.load_config()
    assert cfg.mode == "claude_only"
    assert cfg.max_context_chars == 5000
