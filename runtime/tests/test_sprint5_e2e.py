"""TDD: Sprint 5 — E2E + Cron + Visual test executors."""

from __future__ import annotations

import pytest


class TestE2EExecutor:
    """Playwright-based E2E test execution."""

    def test_e2e_module_imports(self):
        """E2E executor should be importable."""
        from runtime.testing.e2e import E2EExecutor, E2EConfig
        assert E2EExecutor is not None
        assert E2EConfig is not None

    def test_e2e_config_defaults(self):
        """E2E config should have sensible defaults."""
        from runtime.testing.e2e import E2EConfig
        cfg = E2EConfig()
        assert cfg.browser in ("chromium", "firefox", "webkit")
        assert cfg.timeout_seconds > 0
        assert cfg.headless is True

    def test_e2e_simple_check(self):
        """Simple page load check should work."""
        from runtime.testing.e2e import E2EExecutor, E2EConfig
        cfg = E2EConfig(headless=True, timeout_seconds=10)
        executor = E2EExecutor(cfg)
        result = executor.check_page("https://example.com")
        assert result.status == "pass"
        assert result.url == "https://example.com"


class TestCronScheduler:
    """Cron-based scheduled test execution."""

    def test_scheduler_imports(self):
        """Cron scheduler should be importable with run/tick functions."""
        from runtime.scheduler.scheduler import run_job, tick, run_forever, start_background
        assert callable(run_job)
        assert callable(tick)
        assert callable(run_forever)
        assert callable(start_background)

    def test_run_job_executes(self):
        """run_job should execute a job and return results."""
        from runtime.scheduler.scheduler import run_job
        job = {"id": "test-job-001", "name": "test-job", "cron": "* * * * *", "prompt": "echo hello"}
        result = run_job(job)
        assert result is not None
        assert "ok" in result or "output" in result

    def test_tick_runs_without_error(self):
        """tick() should run without exception."""
        from runtime.scheduler.scheduler import tick
        count = tick()
        assert isinstance(count, int)
        assert count >= 0
