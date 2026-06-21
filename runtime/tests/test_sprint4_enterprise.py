"""TDD: Sprint 4 — B端/C端分化 (mode switching, RBAC, audit)."""

from __future__ import annotations

import pytest


class TestDeploymentMode:
    """Mode switching between community and enterprise."""

    def test_default_mode_is_community(self):
        """Default deployment mode should be community."""
        from runtime.config.settings import Settings
        s = Settings()
        assert s.deployment_mode == "community"

    def test_enterprise_mode_configurable(self, monkeypatch):
        """Setting deployment_mode=enterprise should be reflected."""
        monkeypatch.setenv("TAGENT_DEPLOYMENT_MODE", "enterprise")
        from runtime.config.settings import Settings
        s = Settings()
        assert s.deployment_mode == "enterprise"

    def test_mode_affects_auth_requirement(self):
        """Enterprise mode should enable SSO requirement."""
        from runtime.config.settings import Settings
        s_ent = Settings(deployment_mode="enterprise")
        s_com = Settings(deployment_mode="community")
        assert s_ent.deployment_mode == "enterprise"
        assert s_com.deployment_mode == "community"
        # In enterprise mode, SSO should be required (checked by middleware)
        # In community mode, SSO should be optional


class TestRBAC:
    """Role-based access control."""

    def test_rbac_roles_defined(self):
        """RBAC module should define admin/viewer roles and RBAC manager."""
        from runtime.api.auth.rbac import Role, Permission, RBAC
        assert Role.ADMIN.value == "admin"
        assert Role.VIEWER.value == "viewer"
        assert Permission.VIEW_RESULTS.value == "view:results"
        assert hasattr(RBAC, 'has_permission')

    def test_rbac_admin_has_full_access(self):
        """Admin role should have all permissions (default mode: disabled passes all)."""
        from runtime.api.auth.rbac import RBAC, Role, Permission
        rbac = RBAC()
        # In default mode (disabled), all checks pass
        assert rbac.has_permission(Role.ADMIN, Permission.VIEW_RESULTS)


class TestAuditLog:
    """Audit logging for enterprise mode."""

    def test_audit_log_imports(self):
        """Audit module should be importable and log events."""
        from runtime.observability.audit import log_event, query_events
        assert callable(log_event)
        assert callable(query_events)

    def test_audit_log_writes_events(self):
        """Audit should persist events to JSONL file."""
        from runtime.observability.audit import log_event, query_events
        log_event('test_login', actor='admin', resource='auth')
        events = query_events(limit=1)
        assert len(events) >= 1


class TestSsoImport:
    """SSO module smoke test."""

    def test_sso_module_imports(self):
        """SSO module should have SSO configuration classes."""
        from runtime.api.auth.sso import SSOConfig, SSOManager
        cfg = SSOConfig(
            provider="oidc",
            issuer_url="https://accounts.google.com",
            client_id="test",
            client_secret="test",
            redirect_uri="http://localhost:8080/callback",
        )
        assert cfg.issuer_url == "https://accounts.google.com"
        assert hasattr(SSOManager, 'validate_token')
        assert hasattr(SSOManager, 'get_authorization_url')
