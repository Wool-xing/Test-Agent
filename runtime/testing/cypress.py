"""Cypress E2E test executor — alternative to Playwright (Sprint 5)."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CypressConfig:
    timeout_seconds: int = 60
    browser: str = "chromium"
    headless: bool = True
    spec_pattern: str = "cypress/e2e/**/*.cy.js"


@dataclass
class CypressResult:
    status: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    summary: str = ""
    error: str | None = None
    duration_ms: int = 0


class CypressExecutor:
    """Execute Cypress E2E tests."""

    def __init__(self, config: CypressConfig | None = None):
        self._config = config or CypressConfig()

    def run(self, project_dir: str = ".") -> CypressResult:
        """Run Cypress tests in the specified project directory."""
        import time

        start = time.monotonic()
        args = [
            "npx", "cypress", "run",
            "--browser", self._config.browser,
            "--spec", self._config.spec_pattern,
        ]
        if self._config.headless:
            args.append("--headless")

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=self._config.timeout_seconds,
                cwd=project_dir,
            )
            elapsed = int((time.monotonic() - start) * 1000)
            output = result.stdout + result.stderr

            # Parse Cypress output
            import re
            passed = 0
            failed = 0
            m = re.search(r"(\d+)\s+passing", output)
            if m:
                passed = int(m.group(1))
            m = re.search(r"(\d+)\s+failing", output)
            if m:
                failed = int(m.group(1))

            return CypressResult(
                status="pass" if failed == 0 and result.returncode == 0 else "fail",
                total=passed + failed,
                passed=passed,
                failed=failed,
                summary=f"Cypress: {passed} passed, {failed} failed",
                duration_ms=elapsed,
            )
        except FileNotFoundError:
            return CypressResult(status="error", error="Cypress not installed. Run: npm install cypress")
        except subprocess.TimeoutExpired:
            return CypressResult(status="error", error=f"Cypress timed out after {self._config.timeout_seconds}s")
        except Exception as exc:
            return CypressResult(status="error", error=str(exc))
