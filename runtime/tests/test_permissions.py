"""TDD tests for Permission Manager (Sprint 2 P1-004)."""

import pytest

from runtime.agent.permissions import (
    PermissionManager,
    PermissionLevel,
    PermissionDecision,
    get_permission_manager,
)


class TestPermissionManager:
    def test_builtin_deny_destructive(self):
        """Destructive operations should be denied."""
        pm = PermissionManager()
        decision = pm.check("Bash", "rm -rf /")
        assert decision.allowed is False
        assert decision.level == PermissionLevel.DENY

    def test_builtin_allow_safe(self):
        """Safe operations should be allowed."""
        pm = PermissionManager()
        decision = pm.check("Read", "src/main.py")
        assert decision.allowed is True
        assert decision.level == PermissionLevel.ALLOW

    def test_builtin_deny_env_file(self):
        """.env files should be denied for write."""
        pm = PermissionManager()
        decision = pm.check("Write", ".env")
        assert decision.allowed is False

    def test_custom_rule(self):
        """Custom rules should override defaults."""
        pm = PermissionManager()
        pm.add_rule("Bash(custom *)", PermissionLevel.ALLOW)
        decision = pm.check("Bash", "custom script")
        assert decision.allowed is True

    def test_destructive_detection(self):
        """check_destructive should flag dangerous commands."""
        pm = PermissionManager()
        assert pm.check_destructive("rm -rf /tmp") is True
        assert pm.check_destructive("sudo reboot") is True
        assert pm.check_destructive("echo hello") is False

    def test_workspace_write_allowed(self):
        """Write to workspace should be allowed."""
        pm = PermissionManager()
        decision = pm.check("Write", "workspace/output.txt")
        assert decision.allowed is True

    def test_singleton(self):
        """get_permission_manager should return same instance."""
        pm1 = get_permission_manager()
        pm2 = get_permission_manager()
        assert pm1 is pm2
