import os
import stat
import subprocess
from pathlib import Path

from sieve import shim


def test_write_and_remove_shim(tmp_path: Path, monkeypatch):
    bin_dir = tmp_path / "bin"
    shim_path = bin_dir / "claude"
    monkeypatch.setattr(shim, "BIN_DIR", bin_dir)
    monkeypatch.setattr(shim, "SHIM_PATH", shim_path)

    written = shim.write_shim("/usr/local/bin/claude")
    assert written == shim_path
    assert shim_path.is_file()
    assert os.access(shim_path, os.X_OK)
    content = shim_path.read_text()
    assert "run claude" in content
    assert "/usr/local/bin/claude" in content

    assert shim.remove_shim() is True
    assert not shim_path.exists()
    assert shim.remove_shim() is False


def test_shim_falls_back_to_real_claude_when_sieve_missing(tmp_path: Path, monkeypatch):
    bin_dir = tmp_path / "bin"
    shim_path = bin_dir / "claude"
    monkeypatch.setattr(shim, "BIN_DIR", bin_dir)
    monkeypatch.setattr(shim, "SHIM_PATH", shim_path)
    monkeypatch.setattr(shim, "_sieve_executable", lambda: str(tmp_path / "deleted-venv" / "sieve"))

    real = tmp_path / "real-claude"
    real.write_text('#!/usr/bin/env bash\necho "real:$1"\n')
    real.chmod(0o755)

    shim.write_shim(str(real))
    result = subprocess.run([str(shim_path), "hello"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "real:hello"
    assert "passing through" in result.stderr


def test_shim_exits_127_when_nothing_executable(tmp_path: Path, monkeypatch):
    bin_dir = tmp_path / "bin"
    shim_path = bin_dir / "claude"
    monkeypatch.setattr(shim, "BIN_DIR", bin_dir)
    monkeypatch.setattr(shim, "SHIM_PATH", shim_path)
    monkeypatch.setattr(shim, "_sieve_executable", lambda: str(tmp_path / "missing-sieve"))

    shim.write_shim(str(tmp_path / "missing-claude"))
    result = subprocess.run([str(shim_path)], capture_output=True, text=True)
    assert result.returncode == 127
    assert "shim" in result.stderr


def test_find_real_claude_excludes_sieve_bin(tmp_path: Path, monkeypatch):
    bin_dir = tmp_path / "sievebin"
    bin_dir.mkdir()
    fake_shim = bin_dir / "claude"
    fake_shim.write_text("#!/usr/bin/env bash\necho fake\n")
    fake_shim.chmod(fake_shim.stat().st_mode | stat.S_IEXEC)

    real_dir = tmp_path / "usr_local_bin"
    real_dir.mkdir()
    real_claude = real_dir / "claude"
    real_claude.write_text("#!/usr/bin/env bash\necho real\n")
    real_claude.chmod(real_claude.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setattr(shim, "BIN_DIR", bin_dir)

    path_env = f"{bin_dir}{os.pathsep}{real_dir}"
    found = shim.find_real_claude(path_env=path_env)
    assert found == str(real_claude)


def test_path_order_correct(tmp_path: Path, monkeypatch):
    bin_dir = tmp_path / "sievebin"
    bin_dir.mkdir()
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    (other_dir / "claude").write_text("echo real")

    monkeypatch.setattr(shim, "BIN_DIR", bin_dir)

    good_path = f"{bin_dir}{os.pathsep}{other_dir}"
    bad_path = f"{other_dir}{os.pathsep}{bin_dir}"
    assert shim.path_order_correct(path_env=good_path) is True
    assert shim.path_order_correct(path_env=bad_path) is False


def test_persist_path_appends_once(tmp_path: Path):
    rc_path = tmp_path / ".zshrc"
    rc_path.write_text("existing config\n")

    assert shim.persist_path(rc_path) is True
    contents = rc_path.read_text()
    assert shim.PATH_MARKER in contents
    assert 'export PATH="$HOME/.sieve/bin:$PATH"' in contents

    # Second call is idempotent — no duplicate line.
    assert shim.persist_path(rc_path) is False
    assert contents.count(shim.PATH_MARKER) == rc_path.read_text().count(shim.PATH_MARKER)
    assert rc_path.read_text().count(shim.PATH_MARKER) == 1
