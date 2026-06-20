"""TDD tests for tagent report command."""

import subprocess
import sys
from pathlib import Path

import pytest


def _run_report(*args: str) -> subprocess.CompletedProcess:
    """Run tagent report with given args, return CompletedProcess."""
    env = {**__import__("os").environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run(
        [sys.executable, "-m", "runtime.cli.main", "report", *args],
        capture_output=True, text=True, timeout=15, env=env,
    )


class TestReportCommand:
    def test_report_help(self):
        """tagent report --help should work."""
        r = _run_report("--help")
        assert r.returncode == 0

    def test_report_no_runs(self):
        """tagent report with no prior runs should not crash."""
        r = _run_report()
        # exit code 0 means handled gracefully
        assert r.returncode == 0

    def test_report_history_flag(self):
        """tagent report --history should not crash."""
        r = _run_report("--history")
        assert r.returncode == 0
