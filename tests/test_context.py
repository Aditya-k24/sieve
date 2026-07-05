from pathlib import Path

from sieve.context import gather_context


def test_package_json_extraction(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts": {"test": "jest"}}')
    ctx = gather_context("what scripts are in package.json?", tmp_path)
    assert ctx is not None
    assert "jest" in ctx


def test_readme_extraction(tmp_path: Path):
    (tmp_path / "README.md").write_text("# My Project\nUses pytest.")
    ctx = gather_context("summarize the readme", tmp_path)
    assert ctx is not None
    assert "pytest" in ctx


def test_test_framework_manifest_detection(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    ctx = gather_context("what test framework is used?", tmp_path)
    assert ctx is not None
    assert "pytest" in ctx


def test_no_relevant_file_returns_none(tmp_path: Path):
    ctx = gather_context("what test framework is used?", tmp_path)
    assert ctx is None


def test_huge_explicit_file_returns_none(tmp_path: Path):
    big_file = tmp_path / "big.py"
    big_file.write_text("x = 1\n" * 20000)
    ctx = gather_context("explain this file big.py", tmp_path, max_chars=100)
    assert ctx is None
