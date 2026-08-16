"""Verify all CLI commands are registered and --version works."""

from __future__ import annotations

from typer.testing import CliRunner

from runtime.cli.main import app

runner = CliRunner()

EXPECTED_COMMANDS = [
    "catalog", "demo", "doctor", "export", "init",
    "install", "uninstall", "verify",
    "run", "selftest",
]


def test_all_commands_registered():
    """Every expected command appears in --help output."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in EXPECTED_COMMANDS:
        assert cmd in result.stdout, f"command '{cmd}' missing from CLI"


def test_version_flag():
    """--version prints version and exits 0."""
    import re

    from runtime import __version__
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    # Rich console adds ANSI codes — strip them
    clean = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
    assert __version__ in clean


def test_catalog_command():
    """catalog outputs experts + skills without crashing."""
    result = runner.invoke(app, ["catalog"])
    assert result.exit_code == 0
    assert "experts" in result.stdout
    assert "skills" in result.stdout


def test_doctor_command():
    """doctor runs without crashing."""
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "Settings" in result.stdout


def test_help_per_command():
    """Each command has its own --help."""
    for cmd in EXPECTED_COMMANDS:
        result = runner.invoke(app, [cmd, "--help"])
        assert result.exit_code == 0, f"{cmd} --help failed"
        assert result.stdout.strip(), f"{cmd} --help produced no output"


def test_run_exits_nonzero_when_tests_fail(monkeypatch):
    """`tagent run` must exit 1 when the run summary reports failures."""
    from types import SimpleNamespace

    from runtime.cli import _shared
    from runtime.cli.commands import run as run_mod

    def fake_submit(art, persist=True):
        decision = SimpleNamespace(
            detected_target_type="web-system",
            confidence=0.5,
            rationale="fake",
            dag=[],
        )
        return "fake-run-id", decision

    def fake_execute_sync(run_id, decision):
        return {"total": 3, "succeeded": 2, "failed": 1, "skipped": 0}

    monkeypatch.setattr(run_mod._kernel, "submit", fake_submit)
    monkeypatch.setattr(run_mod._kernel, "execute_sync", fake_execute_sync)
    monkeypatch.setattr(_shared, "print_dag", lambda decision: None)

    result = runner.invoke(app, ["run", "login page test"])
    assert result.exit_code == 1, f"expected exit 1 on failures, got {result.exit_code}"
