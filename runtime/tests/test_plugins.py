"""Minimal plugin framework tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from runtime.plugins import discover_plugins


def _write_plugin(plugins_dir: Path, name: str, body: str) -> Path:
    """Write a plugin .py file and return its path."""
    plugins_dir.mkdir(parents=True, exist_ok=True)
    p = plugins_dir / f"{name}.py"
    p.write_text(body, encoding="utf-8")
    return p


class TestPluginDiscovery:
    """Plugin hot-loading from workspace/plugins/."""

    def test_empty_dir_returns_empty(self, tmp_path: Path):
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        result = discover_plugins(plugins_dir)
        assert result == {}

    def test_missing_dir_returns_empty(self, tmp_path: Path):
        result = discover_plugins(tmp_path / "nonexistent")
        assert result == {}

    def test_valid_plugin_loaded(self, tmp_path: Path):
        plugins_dir = tmp_path / "plugins"
        _write_plugin(plugins_dir, "hello", """
def register():
    return {"name": "hello", "description": "A test plugin", "run": lambda text: f"hello: {text}"}
""")
        loaded = discover_plugins(plugins_dir)
        assert "hello" in loaded
        info = loaded["hello"].register()
        assert info["name"] == "hello"
        assert info["description"] == "A test plugin"
        assert info["run"]("world") == "hello: world"

    def test_underscore_files_skipped(self, tmp_path: Path):
        plugins_dir = tmp_path / "plugins"
        _write_plugin(plugins_dir, "_internal", """
def register():
    return {}
""")
        loaded = discover_plugins(plugins_dir)
        assert "_internal" not in loaded

    def test_invalid_plugin_does_not_crash(self, tmp_path: Path):
        plugins_dir = tmp_path / "plugins"
        _write_plugin(plugins_dir, "broken", "syntax error {{{")
        # Should not raise — just skip the broken plugin
        loaded = discover_plugins(plugins_dir)
        assert "broken" not in loaded

    def test_no_register_function_skipped(self, tmp_path: Path):
        plugins_dir = tmp_path / "plugins"
        _write_plugin(plugins_dir, "noapi", "x = 1")
        loaded = discover_plugins(plugins_dir)
        assert "noapi" not in loaded


class TestPluginCLI:
    """CLI plugin commands exist."""

    def test_plugin_command_registered(self):
        """Verify plugin subcommand is accessible."""
        from typer.testing import CliRunner
        from runtime.cli.main import app
        runner = CliRunner()
        result = runner.invoke(app, ["plugin", "--help"])
        assert result.exit_code == 0
        assert "scaffold" in result.stdout
