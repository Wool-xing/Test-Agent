"""Unit test executor — run pytest on test files (Sprint 5)."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class UnitTestConfig:
    timeout_seconds: int = 60
    coverage: bool = False
    verbose: bool = False


@dataclass
class UnitTestResult:
    status: str  # pass | fail | error
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    coverage_pct: float = 0.0
    summary: str = ""
    error: str | None = None
    duration_ms: int = 0


class UnitTestExecutor:
    """Execute unit tests using pytest."""

    def __init__(self, config: UnitTestConfig | None = None):
        self._config = config or UnitTestConfig()

    def run(self, test_paths: list[str]) -> UnitTestResult:
        """Run pytest on specified test files or directories."""
        import time
        import re

        start = time.monotonic()
        args = [sys.executable, "-m", "pytest", "-q", "--no-header", "--tb=short"]

        if self._config.verbose:
            args.append("-v")
        if self._config.coverage:
            args.extend(["--cov=runtime", "--cov-report=term"])

        args.extend(test_paths)

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self._config.timeout_seconds,
            )
            output = result.stdout + result.stderr
            elapsed = int((time.monotonic() - start) * 1000)

            # Parse pytest output
            passed = 0
            failed = 0
            errors = 0
            for line in output.split("\n"):
                m = re.search(r"(\d+)\s+passed", line)
                if m:
                    passed = int(m.group(1))
                m = re.search(r"(\d+)\s+failed", line)
                if m:
                    failed = int(m.group(1))
                m = re.search(r"(\d+)\s+errors?", line)
                if m:
                    errors = int(m.group(1))

            coverage = 0.0
            cov_match = re.search(r"TOTAL.*?(\d+)%", output)
            if cov_match:
                coverage = float(cov_match.group(1))

            return UnitTestResult(
                status="pass" if failed == 0 and errors == 0 else "fail",
                total=passed + failed + errors,
                passed=passed,
                failed=failed,
                errors=errors,
                coverage_pct=coverage,
                summary=f"{passed} passed, {failed} failed, {errors} errors",
                duration_ms=elapsed,
            )
        except subprocess.TimeoutExpired:
            return UnitTestResult(
                status="error",
                error=f"Test execution timed out after {self._config.timeout_seconds}s",
                duration_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as exc:
            return UnitTestResult(
                status="error",
                error=str(exc),
                duration_ms=int((time.monotonic() - start) * 1000),
            )
