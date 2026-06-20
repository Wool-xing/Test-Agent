"""TDD tests for Deployment Rollback (§补-23)."""

from runtime.infra.rollback import RollbackManager, get_rollback_manager


class TestRollbackManager:
    def test_create_point(self):
        """Should create a rollback point."""
        rm = RollbackManager()
        point = rm.create_point("V2.0.0", db_revision="abc123")
        assert point.version == "V2.0.0"
        assert point.db_revision == "abc123"

    def test_latest_point(self):
        """Should return latest rollback point."""
        rm = RollbackManager()
        rm.create_point("V2.0.0")
        rm.create_point("V2.1.0")
        assert rm.latest.version == "V2.1.0"

    def test_rollback(self):
        """Rollback should return and remove latest point."""
        rm = RollbackManager()
        rm.create_point("V2.0.0")
        rm.create_point("V2.1.0")
        point = rm.rollback()
        assert point.version == "V2.1.0"
        assert rm.latest.version == "V2.0.0"

    def test_should_rollback_smoke_failure(self):
        """Smoke test failure should trigger rollback."""
        rm = RollbackManager()
        assert rm.should_rollback(False, 1.0, 0) is True

    def test_should_rollback_low_install_rate(self):
        """Low install success rate should trigger rollback."""
        rm = RollbackManager()
        assert rm.should_rollback(True, 0.90, 0) is True

    def test_should_rollback_critical_bugs(self):
        """3+ critical bugs should trigger rollback."""
        rm = RollbackManager()
        assert rm.should_rollback(True, 1.0, 3) is True

    def test_should_not_rollback_normal(self):
        """Normal conditions should not trigger rollback."""
        rm = RollbackManager()
        assert rm.should_rollback(True, 0.99, 1) is False

    def test_singleton(self):
        """get_rollback_manager should return singleton."""
        r1 = get_rollback_manager()
        r2 = get_rollback_manager()
        assert r1 is r2
