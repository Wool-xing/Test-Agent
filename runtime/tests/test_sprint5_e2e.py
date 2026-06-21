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


class TestVisualExecutor:
    """Screenshot-based visual regression testing."""

    def test_visual_module_imports(self):
        """Visual executor should be importable."""
        from runtime.testing.visual import VisualExecutor, VisualConfig
        assert VisualExecutor is not None
        assert VisualConfig is not None

    def test_visual_config_defaults(self):
        """Visual config should have sensible defaults."""
        from runtime.testing.visual import VisualConfig
        cfg = VisualConfig()
        assert 0 < cfg.threshold < 1.0
        assert cfg.output_dir == "workspace/visual-tests"

    def test_compare_missing_baseline_fails(self, tmp_path):
        """Compare without baseline should return error."""
        from runtime.testing.visual import VisualExecutor, VisualConfig
        cfg = VisualConfig(output_dir=str(tmp_path))
        executor = VisualExecutor(cfg)
        result = executor.compare("https://example.com", "nonexistent")
        assert result.status == "error"
        assert "Baseline not found" in (result.error or "")


class TestIntegrationExecutor:
    """API + DB integration testing."""

    def test_integration_module_imports(self):
        """Integration executor should be importable."""
        from runtime.testing.integration import IntegrationExecutor, IntegrationConfig, ApiCheck
        assert IntegrationExecutor is not None

    def test_api_check_basic(self):
        """Basic API check against a test endpoint."""
        from runtime.testing.integration import IntegrationExecutor, ApiCheck
        executor = IntegrationExecutor()
        checks = [ApiCheck(method="GET", path="/get", expected_status=200)]
        result = executor.check_api("https://httpbin.org", checks)
        assert result.status in ("pass", "fail", "error")  # network-dependent

    def test_db_check_in_memory(self, tmp_path):
        """DB check against SQLite in-memory database."""
        import sqlite3
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.execute("INSERT INTO test VALUES (1)")
        conn.commit()
        conn.close()

        from runtime.testing.integration import IntegrationExecutor
        executor = IntegrationExecutor()
        result = executor.check_db(f"sqlite:///{db_path}", "SELECT * FROM test", expected_rows_min=1)
        assert result.status == "pass"


class TestPentestSkills:
    """Verify existing pentest skills are importable."""

    def test_pentest_modules_exist(self):
        """Pentest skill modules should be importable."""
        modules = [
            "runtime.orchestrator.skills.pentest_coordinator",
            "runtime.orchestrator.skills.pentest_recon",
            "runtime.orchestrator.skills.pentest_vuln",
            "runtime.orchestrator.skills.pentest_api",
            "runtime.orchestrator.skills.pentest_web",
        ]
        import importlib
        for mod in modules:
            try:
                importlib.import_module(mod)
            except ImportError as e:
                pytest.fail(f"Failed to import {mod}: {e}")


class TestCypressExecutor:
    """Cypress E2E test executor."""

    def test_cypress_module_imports(self):
        """Cypress executor should be importable."""
        from runtime.testing.cypress import CypressExecutor, CypressConfig
        assert CypressExecutor is not None

    def test_cypress_not_installed_graceful(self):
        """Cypress executor should handle missing Cypress gracefully."""
        from runtime.testing.cypress import CypressExecutor
        executor = CypressExecutor()
        result = executor.run("/nonexistent")
        assert result.status == "error"
        assert "not installed" in (result.error or "").lower()


class TestMobileExecutor:
    """Mobile test executor (Appium)."""

    def test_mobile_module_imports(self):
        """Mobile executor should be importable."""
        from runtime.testing.mobile import MobileExecutor, MobileConfig
        assert MobileExecutor is not None

    def test_mobile_appium_check(self):
        """Mobile executor should handle missing Appium gracefully."""
        from runtime.testing.mobile import MobileExecutor
        executor = MobileExecutor()
        result = executor.check_installed()
        assert result.status in ("pass", "error")

    def test_mobile_run_test(self):
        """run_test should work without Appium server."""
        from runtime.testing.mobile import MobileExecutor
        executor = MobileExecutor()
        result = executor.run_test("test_login.py")
        assert result.status == "pass"
        assert len(result.checks) >= 2
