"""TDD tests for §补-1 Migration, §补-2 AutoUpdate, §补-3 Telemetry."""

import tempfile
from pathlib import Path

from runtime.infra.migration import MigrationManager, MigrationReport
from runtime.infra.auto_update import UpdateChecker, UpdateInfo
from runtime.infra.telemetry import TelemetryManager, TelemetryConfig, CommandMetric


# ── §补-1 Migration ─────────────────────────────────────

class TestMigration:
    def test_check_not_needed(self):
        """Fresh project should not need migration."""
        mgr = MigrationManager(Path(tempfile.mkdtemp()))
        assert mgr.check_needed() is False

    def test_dry_run(self):
        """Dry run should produce report without changes."""
        mgr = MigrationManager(Path(tempfile.mkdtemp()))
        report = mgr.dry_run()
        assert len(report.steps) == 4

    def test_migrate_fresh_project(self):
        """Migration on fresh project should succeed."""
        mgr = MigrationManager(Path(tempfile.mkdtemp()))
        report = mgr.migrate()
        assert len(report.steps) >= 1  # Skills step always applied


# ── §补-2 AutoUpdate ─────────────────────────────────────

class TestAutoUpdate:
    def test_update_checker_initial(self):
        """Update checker should start with current version."""
        checker = UpdateChecker("V2.0.0")
        info = checker.check()
        assert info.current_version == "V2.0.0"

    def test_version_comparison(self):
        """Should correctly compare versions."""
        checker = UpdateChecker("V2.0.0")
        assert checker._is_newer("V2.1.0") is True
        assert checker._is_newer("V2.0.0") is False
        assert checker._is_newer("V1.9.0") is False


# ── §补-3 Telemetry ─────────────────────────────────────

class TestTelemetry:
    def test_disabled_by_default(self):
        """Telemetry should be off by default."""
        tm = TelemetryManager(Path(tempfile.mkdtemp()))
        assert tm.config.enabled is False
        assert tm.config.usage_stats is False

    def test_enable_disable(self):
        """Should be able to enable and disable."""
        tm = TelemetryManager(Path(tempfile.mkdtemp()))
        tm.enable("all")
        assert tm.config.enabled is True
        tm.disable()
        assert tm.config.enabled is False

    def test_record_command(self):
        """Recording commands should track metrics."""
        tm = TelemetryManager(Path(tempfile.mkdtemp()))
        tm.enable("usage")
        tm.record_command("run", 150)
        tm.record_command("run", 250)
        stats = tm.get_stats()
        assert "run" in stats["commands"]
        assert stats["commands"]["run"]["count"] == 2

    def test_record_command_disabled(self):
        """Should not record when disabled."""
        tm = TelemetryManager(Path(tempfile.mkdtemp()))
        tm.record_command("run", 150)
        stats = tm.get_stats()
        assert stats["total_commands"] == 0

    def test_p50_p95(self):
        """Percentile calculations should work."""
        metric = CommandMetric(command="test", durations=list(range(1, 101)))  # 1..100
        assert metric.p50 == 50
        assert metric.p95 == 95
