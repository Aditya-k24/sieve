import json
from pathlib import Path

from sieve import statusline


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
