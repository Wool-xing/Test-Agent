"""TDD tests for Graceful Degradation (§补-10)."""

from runtime.infra.degradation import (
    DegradationManager,
    DegradationLevel,
    check_disk_space,
    get_degradation_manager,
)


class TestDegradationManager:
    def test_initial_normal(self):
        """Fresh manager should report NORMAL."""
        dm = DegradationManager()
        assert dm.overall_level == DegradationLevel.NORMAL
        assert len(dm.active_events) == 0

    def test_single_degradation(self):
        """Single degradation event should be tracked."""
        dm = DegradationManager()
        dm.degrade("llm", DegradationLevel.DEGRADED, "API key missing")
        assert dm.overall_level == DegradationLevel.DEGRADED
        assert len(dm.active_events) == 1

    def test_recovery(self):
        """Recovery should clear degradation."""
        dm = DegradationManager()
        dm.degrade("network", DegradationLevel.DEGRADED, "Disconnected")
        assert dm.overall_level == DegradationLevel.DEGRADED
        dm.recover("network")
        assert dm.overall_level == DegradationLevel.NORMAL

    def test_critical_overrides_degraded(self):
        """CRITICAL should override DEGRADED."""
        dm = DegradationManager()
        dm.degrade("llm", DegradationLevel.DEGRADED, "Slow")
        dm.degrade("disk", DegradationLevel.CRITICAL, "Disk full")
        assert dm.overall_level == DegradationLevel.CRITICAL

    def test_multiple_components(self):
        """Multiple independent degradations tracked separately."""
        dm = DegradationManager()
        dm.degrade("llm", DegradationLevel.DEGRADED, "API key missing")
        dm.degrade("mcp", DegradationLevel.DEGRADED, "Server down")
        assert len(dm.active_events) == 2
        dm.recover("llm")
        assert len(dm.active_events) == 1
        assert dm.active_events[0].component == "mcp"

    def test_summary(self):
        """Summary should describe active degradations."""
        dm = DegradationManager()
        dm.degrade("db", DegradationLevel.MINIMAL, "Connection refused")
        assert "db" in dm.summary()
        assert "Connection refused" in dm.summary()

    def test_singleton(self):
        """get_degradation_manager should return same instance."""
        dm1 = get_degradation_manager()
        dm2 = get_degradation_manager()
        assert dm1 is dm2


class TestDiskSpaceCheck:
    def test_disk_space_check_returns_bool(self):
        """check_disk_space should return True/False."""
        result = check_disk_space(min_mb=1)
        assert isinstance(result, bool)
