from sieve import claude_runner


class _FakeCompletedProcess:
    def __init__(self, returncode: int = 0):
        self.returncode = returncode


def test_run_claude_adds_model_override(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeCompletedProcess(0)

    monkeypatch.setattr(claude_runner.subprocess, "run", fake_run)

    result = claude_runner.run_claude("/usr/local/bin/claude", ["fix the bug"], model_override="sonnet")
    assert captured["cmd"] == ["/usr/local/bin/claude", "--model", "sonnet", "fix the bug"]
    assert result.exit_code == 0


def test_run_claude_skips_override_if_user_already_set_model(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeCompletedProcess(0)

    monkeypatch.setattr(claude_runner.subprocess, "run", fake_run)

    result = claude_runner.run_claude(
        "/usr/local/bin/claude", ["--model", "opus", "fix the bug"], model_override="sonnet"
    )
    assert captured["cmd"] == ["/usr/local/bin/claude", "--model", "opus", "fix the bug"]
    assert result.exit_code == 0


def test_run_claude_no_override_when_none(monkeypatch):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeCompletedProcess(0)

    monkeypatch.setattr(claude_runner.subprocess, "run", fake_run)

    claude_runner.run_claude("/usr/local/bin/claude", ["fix the bug"], model_override=None)
    assert captured["cmd"] == ["/usr/local/bin/claude", "fix the bug"]
