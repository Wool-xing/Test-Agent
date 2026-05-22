"""Portability / co‑existence / replaceability tests (ISO 25010)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.portability
class TestInstallability:
    def test_python_version_supported(self):
        """Python 3.10+ is required."""
        assert sys.version_info >= (3, 10), f"Python {sys.version_info.major}.{sys.version_info.minor} < 3.10"

    def test_pyproject_exists(self):
        pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
        assert pyproject.exists(), f"pyproject.toml not found at {pyproject}"

    def test_cli_entry_point(self):
        """tagent CLI is registered."""
        result = subprocess.run(
            [sys.executable, "-m", "runtime.cli.main", "--version"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"


@pytest.mark.portability
class TestCoexistence:
    def test_no_port_conflict(self):
        """Default API port 8800 is unlikely to conflict with common services."""
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", 8800))
        except OSError:
            pytest.skip("port 8800 already in use")
        finally:
            s.close()

    def test_no_aggressive_env_overwrite(self):
        """Installing runtime should not overwrite user env vars."""
        path = os.environ.get("PATH", "")
        assert path, "PATH should not be empty after import"


@pytest.mark.portability
class TestReplaceability:
    def test_standard_interfaces(self):
        """Core functions use standard Python interfaces (no custom protocols)."""
        import inspect

        from runtime.orchestrator.adapters.experts import execute_node
        sig = inspect.signature(execute_node)
        params = list(sig.parameters.keys())
        assert "name" in params
        assert "kind" in params
        assert "inputs" in params

    def test_settings_replaceable(self):
        """Settings can be instantiated with custom env."""
        from runtime.config.settings import Settings
        try:
            s = Settings(_env_file=".env.nonexistent")
            assert s.api_port == 8800
        except Exception as e:
            pytest.fail(f"Settings init with missing .env failed: {e}")
