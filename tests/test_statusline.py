import json
import os
import sqlite3
import subprocess
from pathlib import Path

from sieve import statusline

SESSION_JSON = '{"model":{"id":"claude-fable-5","display_name":"Fable 5"}}'


def _setup(tmp_path: Path, monkeypatch, ledger_model: str) -> tuple[Path, dict]:
    """Write the badge script plus a fake SIEVE_HOME with one ledger row."""
    hooks_dir = tmp_path / "hooks"
    monkeypatch.setattr(statusline, "HOOKS_DIR", hooks_dir)
    monkeypatch.setattr(statusline, "SCRIPT_PATH", hooks_dir / "sieve-statusline.sh")
    script_path = statusline.write_script()

    home = tmp_path / "sievehome"
    home.mkdir()
    (home / "config.json").write_text('{"enabled": true}')
    with sqlite3.connect(home / "sieve.db") as conn:
        conn.execute("CREATE TABLE requests (id INTEGER PRIMARY KEY, model TEXT)")
        conn.execute("INSERT INTO requests (model) VALUES (?)", (ledger_model,))
    return script_path, {**os.environ, "SIEVE_HOME": str(home)}


def test_badge_uses_session_model_when_ledger_says_generic_claude(tmp_path: Path, monkeypatch):
    script_path, env = _setup(tmp_path, monkeypatch, ledger_model="claude")
    result = subprocess.run(
        ["bash", str(script_path)], input=SESSION_JSON, capture_output=True, text=True, env=env
    )
    assert "[SIEVE:Fable 5]" in result.stdout


def test_badge_keeps_specific_ledger_model_over_session_model(tmp_path: Path, monkeypatch):
    script_path, env = _setup(tmp_path, monkeypatch, ledger_model="qwen2.5-coder:7b")
    result = subprocess.run(
        ["bash", str(script_path)], input=SESSION_JSON, capture_output=True, text=True, env=env
    )
    assert "[SIEVE:qwen2.5-coder:7b]" in result.stdout


def test_install_fresh_settings(tmp_path: Path, monkeypatch):
    hooks_dir = tmp_path / "hooks"
    script_path = hooks_dir / "sieve-statusline.sh"
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(statusline, "HOOKS_DIR", hooks_dir)
    monkeypatch.setattr(statusline, "SCRIPT_PATH", script_path)

    outcome = statusline.install(settings_path)
    assert outcome == "installed fresh statusLine"
    assert script_path.is_file()

    settings = json.loads(settings_path.read_text())
    assert settings["statusLine"]["type"] == "command"
    assert str(script_path) in settings["statusLine"]["command"]


def test_install_chains_with_existing_statusline(tmp_path: Path, monkeypatch):
    hooks_dir = tmp_path / "hooks"
    script_path = hooks_dir / "sieve-statusline.sh"
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(statusline, "HOOKS_DIR", hooks_dir)
    monkeypatch.setattr(statusline, "SCRIPT_PATH", script_path)

    settings_path.write_text(json.dumps({"statusLine": {"type": "command", "command": "bash other.sh"}}))

    outcome = statusline.install(settings_path)
    assert outcome == "chained into existing statusLine"
    command = json.loads(settings_path.read_text())["statusLine"]["command"]
    assert "other.sh" in command
    assert str(script_path) in command


def test_install_is_idempotent(tmp_path: Path, monkeypatch):
    hooks_dir = tmp_path / "hooks"
    script_path = hooks_dir / "sieve-statusline.sh"
    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr(statusline, "HOOKS_DIR", hooks_dir)
    monkeypatch.setattr(statusline, "SCRIPT_PATH", script_path)

    statusline.install(settings_path)
    second = statusline.install(settings_path)
    assert second == "already installed"

    command = json.loads(settings_path.read_text())["statusLine"]["command"]
    assert command.count(str(script_path)) == 1
