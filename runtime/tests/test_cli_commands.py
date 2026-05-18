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
