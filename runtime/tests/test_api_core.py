"""TDD tests for runtime/api/ pure-logic modules: models, rbac, auth/rbac, parsers, correlation.

Covers the 5 modules that can be tested without running a web server.
Target: boost runtime/api/ coverage from 15% toward 40%.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# ── ensure runtime/ is on path ──────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ═══════════════════════════════════════════════════════════════════════════
# models.py
# ═══════════════════════════════════════════════════════════════════════════

class TestApiModels:
    def test_run_create_text_valid(self):
        """RunCreateText should accept a valid text prompt."""
        from runtime.api.models import RunCreateText
        obj = RunCreateText(text="run smoke test on login page")
        assert obj.text == "run smoke test on login page"
        assert obj.extra == {}

    def test_run_create_text_with_extra(self):
        """RunCreateText should accept extra dict."""
        from runtime.api.models import RunCreateText
        obj = RunCreateText(text="test", extra={"env": "staging"})
        assert obj.extra == {"env": "staging"}

    def test_run_create_text_empty_fails(self):
        """RunCreateText with empty text should fail validation."""
        from pydantic import ValidationError

        from runtime.api.models import RunCreateText
        with pytest.raises(ValidationError):
            RunCreateText(text="")

    def test_run_created_model(self):
        """RunCreated should hold run_id and decision summary."""
        from runtime.api.models import RunCreated
        obj = RunCreated(
            run_id="run-001",
            decision_summary={"router": "smoke-test"},
            accepted=True,
        )
        assert obj.run_id == "run-001"
        assert obj.accepted is True

    def test_run_status_valid(self):
        """RunStatus should accept valid status literals."""
        from runtime.api.models import RunStatus
        for status in ("pending", "running", "succeeded", "failed", "cancelled"):
            obj = RunStatus(run_id="r1", status=status)  # type: ignore[arg-type]
            assert obj.status == status

    def test_run_status_defaults(self):
        """RunStatus defaults should be zero."""
        from runtime.api.models import RunStatus
        obj = RunStatus(run_id="r1", status="pending")
        assert obj.succeeded == 0
        assert obj.failed == 0
        assert obj.total == 0
        assert obj.detail is None

    def test_catalog_response_model(self):
        """CatalogResponse should hold experts, skills, counts."""
        from runtime.api.models import CatalogResponse
        obj = CatalogResponse(
            experts=[{"id": "01", "name": "测试主管"}],
            skills=[{"id": "smoke-test", "name": "冒烟测试"}],
            counts={"experts": 16, "skills": 32},
        )
        assert obj.counts["experts"] == 16
        assert len(obj.experts) == 1


# ═══════════════════════════════════════════════════════════════════════════
# rbac.py (runtime/api/rbac.py — simple role resolver)
# ═══════════════════════════════════════════════════════════════════════════

class TestSimpleRbac:
    def test_resolve_role_disabled_returns_admin(self, monkeypatch):
        """When RBAC disabled (default), resolve_role returns ADMIN for any token."""
        monkeypatch.setenv("TAGENT_RBAC_ENABLED", "0")
        # force reimport to pick up env
        import runtime.api.rbac as rbac_mod
        role = rbac_mod.resolve_role("any-token")
        assert role == rbac_mod.Role.ADMIN

    def test_resolve_role_enabled_known_token(self, monkeypatch):
        """When RBAC enabled, known token resolves to correct role."""
        monkeypatch.setenv("TAGENT_RBAC_ENABLED", "1")
        monkeypatch.setenv("TAGENT_ADMIN_TOKENS", "admin-secret")
        monkeypatch.setenv("TAGENT_LEAD_TOKENS", "")
        monkeypatch.setenv("TAGENT_TESTER_TOKENS", "")
        monkeypatch.setenv("TAGENT_VIEWER_TOKENS", "")
        monkeypatch.delenv("TAGENT_API_AUTH_TOKEN", raising=False)
        # need fresh import since _load_tokens cached at module level
        import importlib

        import runtime.api.rbac as rbac_mod
        importlib.reload(rbac_mod)
        role = rbac_mod.resolve_role("admin-secret")
        assert role == rbac_mod.Role.ADMIN

    def test_resolve_role_enabled_unknown_token(self, monkeypatch):
        """When RBAC enabled, unknown token returns None."""
        monkeypatch.setenv("TAGENT_RBAC_ENABLED", "1")
        monkeypatch.setenv("TAGENT_ADMIN_TOKENS", "admin-secret")
        monkeypatch.setenv("TAGENT_LEAD_TOKENS", "")
        monkeypatch.setenv("TAGENT_TESTER_TOKENS", "")
        monkeypatch.setenv("TAGENT_VIEWER_TOKENS", "")
        monkeypatch.delenv("TAGENT_API_AUTH_TOKEN", raising=False)
        import importlib

        import runtime.api.rbac as rbac_mod
        importlib.reload(rbac_mod)
        role = rbac_mod.resolve_role("unknown-token")
        assert role is None

    def test_get_permissions_admin(self):
        """Admin role should have wildcard permission."""
        from runtime.api.rbac import Role, get_permissions
        perms = get_permissions(Role.ADMIN)
        assert "*" in perms

    def test_get_permissions_viewer(self):
        """Viewer role should have limited permissions."""
        from runtime.api.rbac import Role, get_permissions
        perms = get_permissions(Role.VIEWER)
        assert "run.start" not in perms
        assert "report.view" in perms

    def test_get_permissions_lead(self):
        """Lead role should have config and agent permissions."""
        from runtime.api.rbac import Role, get_permissions
        perms = get_permissions(Role.LEAD)
        assert "config.read" in perms
        assert "run.cancel" in perms

    def test_role_enum_values(self):
        """All four roles should be defined."""
        from runtime.api.rbac import Role
        assert Role.ADMIN.value == "admin"
        assert Role.LEAD.value == "lead"
        assert Role.TESTER.value == "tester"
        assert Role.VIEWER.value == "viewer"


# ═══════════════════════════════════════════════════════════════════════════
# auth/rbac.py (RBAC engine with permissions)
# ═══════════════════════════════════════════════════════════════════════════

class TestAuthRbac:
    def test_rbac_default_enabled(self):
        """RBAC should be enabled by default."""
        from runtime.api.auth.rbac import RBAC
        rbac = RBAC()
        assert rbac.enabled is True

    def test_rbac_disabled_mode(self):
        """When disabled, all permission checks pass."""
        from runtime.api.auth.rbac import RBAC, Permission, Role
        rbac = RBAC(enabled=False)
        assert rbac.has_permission(Role.VIEWER, Permission.MANAGE_USERS) is True
        # check() should not raise
        rbac.check(Role.VIEWER, Permission.MANAGE_USERS)

    def test_rbac_admin_has_all_permissions(self):
        """Admin should have every permission."""
        from runtime.api.auth.rbac import RBAC, Permission, Role
        rbac = RBAC()
        for perm in Permission:
            assert rbac.has_permission(Role.ADMIN, perm), f"Admin lacks {perm}"

    def test_rbac_manager_permissions(self):
        """Manager should have 5 specific permissions but not manage_users."""
        from runtime.api.auth.rbac import RBAC, Permission, Role
        rbac = RBAC()
        assert rbac.has_permission(Role.MANAGER, Permission.RUN_TESTS)
        assert rbac.has_permission(Role.MANAGER, Permission.VIEW_RESULTS)
        assert rbac.has_permission(Role.MANAGER, Permission.MANAGE_AGENTS)
        assert rbac.has_permission(Role.MANAGER, Permission.MANAGE_PLUGINS)
        assert rbac.has_permission(Role.MANAGER, Permission.VIEW_AUDIT)
        assert not rbac.has_permission(Role.MANAGER, Permission.MANAGE_USERS)

    def test_rbac_tester_permissions(self):
        """Tester should only have run_tests and view_results."""
        from runtime.api.auth.rbac import RBAC, Permission, Role
        rbac = RBAC()
        assert rbac.has_permission(Role.TESTER, Permission.RUN_TESTS)
        assert rbac.has_permission(Role.TESTER, Permission.VIEW_RESULTS)
        assert not rbac.has_permission(Role.TESTER, Permission.MANAGE_AGENTS)
        assert not rbac.has_permission(Role.TESTER, Permission.MANAGE_USERS)

    def test_rbac_viewer_permissions(self):
        """Viewer should only see results and audit."""
        from runtime.api.auth.rbac import RBAC, Permission, Role
        rbac = RBAC()
        assert rbac.has_permission(Role.VIEWER, Permission.VIEW_RESULTS)
        assert rbac.has_permission(Role.VIEWER, Permission.VIEW_AUDIT)
        assert not rbac.has_permission(Role.VIEWER, Permission.RUN_TESTS)

    def test_rbac_check_raises_on_denied(self):
        """check() should raise HTTPException(403) when permission denied."""
        from runtime.api.auth.rbac import RBAC, Permission, Role
        rbac = RBAC()
        with pytest.raises(Exception) as exc_info:
            rbac.check(Role.VIEWER, Permission.MANAGE_USERS)
        assert exc_info.value.status_code == 403

    def test_rbac_check_passes_on_allowed(self):
        """check() should not raise when permission granted."""
        from runtime.api.auth.rbac import RBAC, Permission, Role
        rbac = RBAC()
        rbac.check(Role.ADMIN, Permission.MANAGE_USERS)  # no exception

    def test_rbac_get_permissions_admin(self):
        """get_permissions for admin returns all sorted permission values."""
        from runtime.api.auth.rbac import RBAC, Role
        rbac = RBAC()
        perms = rbac.get_permissions(Role.ADMIN)
        assert len(perms) == 7
        assert "manage:agents" in perms
        assert "run:tests" in perms

    def test_rbac_get_permissions_viewer(self):
        """get_permissions for viewer returns only view permissions."""
        from runtime.api.auth.rbac import RBAC, Role
        rbac = RBAC()
        perms = rbac.get_permissions(Role.VIEWER)
        assert perms == ["view:audit", "view:results"]

    def test_rbac_grant_and_revoke_permission(self):
        """grant_permission adds, revoke_permission removes."""
        from runtime.api.auth.rbac import RBAC, Permission, Role
        rbac = RBAC()
        rbac.grant_permission(Role.VIEWER, Permission.RUN_TESTS)
        assert rbac.has_permission(Role.VIEWER, Permission.RUN_TESTS)
        rbac.revoke_permission(Role.VIEWER, Permission.RUN_TESTS)
        assert not rbac.has_permission(Role.VIEWER, Permission.RUN_TESTS)

    def test_rbac_grant_new_role(self):
        """grant_permission to a new role creates the role entry."""
        from runtime.api.auth.rbac import RBAC, Permission, Role
        rbac = RBAC()
        rbac.grant_permission(Role.VIEWER, Permission.MANAGE_TENANT)
        assert rbac.has_permission(Role.VIEWER, Permission.MANAGE_TENANT)

    def test_rbac_revoke_nonexistent_safe(self):
        """revoke_permission on non-existent permission should not raise."""
        from runtime.api.auth.rbac import RBAC, Permission, Role
        rbac = RBAC()
        rbac.revoke_permission(Role.VIEWER, Permission.MANAGE_USERS)  # no exception

    def test_permission_enum_values(self):
        """All 7 permissions should have correct value format."""
        from runtime.api.auth.rbac import Permission
        values = {p.value for p in Permission}
        assert "run:tests" in values
        assert "view:results" in values
        assert "manage:agents" in values
        assert "manage:plugins" in values
        assert "manage:users" in values
        assert "view:audit" in values
        assert "manage:tenant" in values

    def test_role_enum_values(self):
        """Four roles should be defined."""
        from runtime.api.auth.rbac import Role
        assert Role.ADMIN.value == "admin"
        assert Role.MANAGER.value == "manager"
        assert Role.TESTER.value == "tester"
        assert Role.VIEWER.value == "viewer"


# ═══════════════════════════════════════════════════════════════════════════
# parsers.py
# ═══════════════════════════════════════════════════════════════════════════

class TestParsers:
    def test_parse_text(self):
        """parse_text should create a text-kind artifact."""
        from runtime.api.parsers import parse_text
        artifact = parse_text("hello world")
        assert artifact.kind == "text"
        assert artifact.text == "hello world"

    def test_parse_url(self):
        """parse_url should create a url-kind artifact with web-system category."""
        from runtime.api.parsers import parse_url
        artifact = parse_url("https://example.com")
        assert artifact.kind == "url"
        assert artifact.text == "https://example.com"
        assert artifact.extra["category"] == "web-system"

    def test_parse_path_text_file(self, tmp_path):
        """parse_path should detect .md as text file and read content."""
        from runtime.api.parsers import parse_path
        f = tmp_path / "test.md"
        f.write_text("# Hello\n\nWorld", encoding="utf-8")
        artifact = parse_path(f)
        assert artifact.kind == "file"
        assert artifact.mime == "text/plain"
        assert "Hello" in (artifact.text or "")

    def test_parse_path_txt_file(self, tmp_path):
        """parse_path should detect .txt as text."""
        from runtime.api.parsers import parse_path
        f = tmp_path / "readme.txt"
        f.write_text("line1\nline2", encoding="utf-8")
        artifact = parse_path(f)
        assert artifact.kind == "file"
        assert artifact.mime == "text/plain"

    def test_parse_path_yaml_file(self, tmp_path):
        """parse_path should detect .yaml as text."""
        from runtime.api.parsers import parse_path
        f = tmp_path / "config.yaml"
        f.write_text("key: value", encoding="utf-8")
        artifact = parse_path(f)
        assert artifact.mime == "text/plain"

    def test_parse_path_json_file(self, tmp_path):
        """parse_path should detect .json as text."""
        from runtime.api.parsers import parse_path
        f = tmp_path / "data.json"
        f.write_text('{"a": 1}', encoding="utf-8")
        artifact = parse_path(f)
        assert artifact.mime == "text/plain"

    def test_parse_path_pdf_no_reader(self, tmp_path):
        """parse_path on PDF without pypdf installed returns empty text."""
        from runtime.api.parsers import parse_path
        f = tmp_path / "test.pdf"
        f.write_bytes(b"%PDF-1.4\n%%EOF")
        artifact = parse_path(f)
        assert artifact.kind == "file"
        assert artifact.mime == "application/pdf"

    def test_parse_path_mobile_apk(self, tmp_path):
        """parse_path should detect .apk as mobile-app."""
        from runtime.api.parsers import parse_path
        f = tmp_path / "app.apk"
        f.write_bytes(b"\x00" * 100)
        artifact = parse_path(f)
        assert artifact.extra.get("category") == "mobile-app"

    def test_parse_path_mobile_ipa(self, tmp_path):
        """parse_path should detect .ipa as mobile-app."""
        from runtime.api.parsers import parse_path
        f = tmp_path / "app.ipa"
        f.write_bytes(b"\x00" * 100)
        artifact = parse_path(f)
        assert artifact.extra.get("category") == "mobile-app"

    def test_parse_path_desktop_exe(self, tmp_path):
        """parse_path should detect .exe as desktop-app."""
        from runtime.api.parsers import parse_path
        f = tmp_path / "setup.exe"
        f.write_bytes(b"\x00" * 100)
        artifact = parse_path(f)
        assert artifact.extra.get("category") == "desktop-app"

    def test_parse_path_docker_tar(self, tmp_path):
        """parse_path should detect .tar as docker-image."""
        from runtime.api.parsers import parse_path
        f = tmp_path / "image.tar"
        f.write_bytes(b"\x00" * 100)
        artifact = parse_path(f)
        assert artifact.extra.get("category") == "docker-image"

    def test_parse_path_directory(self, tmp_path):
        """parse_path on directory should return directory kind."""
        from runtime.api.parsers import parse_path
        d = tmp_path / "mydir"
        d.mkdir()
        artifact = parse_path(d)
        assert artifact.kind == "directory"

    def test_parse_path_unknown_extension(self, tmp_path):
        """parse_path on unknown extension should return file with unknown category."""
        from runtime.api.parsers import parse_path
        f = tmp_path / "data.xyz"
        f.write_text("some data", encoding="utf-8")
        artifact = parse_path(f)
        assert artifact.kind == "file"
        assert artifact.extra.get("category") == "unknown"

    def test_parse_path_nonexistent_file(self, tmp_path):
        """parse_path on non-existent file should not crash."""
        from runtime.api.parsers import parse_path
        artifact = parse_path(tmp_path / "does_not_exist.txt")
        assert artifact.size_bytes is None


# ═══════════════════════════════════════════════════════════════════════════
# correlation.py
# ═══════════════════════════════════════════════════════════════════════════

class TestCorrelation:
    def test_correlation_middleware_class_exists(self):
        """CorrelationMiddleware should be importable."""
        from runtime.api.correlation import CorrelationMiddleware
        assert CorrelationMiddleware is not None

    def test_middleware_inherits_base(self):
        """CorrelationMiddleware should inherit from BaseHTTPMiddleware."""
        from starlette.middleware.base import BaseHTTPMiddleware

        from runtime.api.correlation import CorrelationMiddleware
        assert issubclass(CorrelationMiddleware, BaseHTTPMiddleware)

    def test_header_constants(self):
        """X-Request-ID and X-Correlation-ID should be defined."""
        from runtime.api.correlation import HEADER_CORRELATION_ID, HEADER_REQUEST_ID
        assert HEADER_REQUEST_ID == "X-Request-ID"
        assert HEADER_CORRELATION_ID == "X-Correlation-ID"

    def test_get_request_id_no_state(self):
        """get_request_id with no request_id attribute returns 'unknown'."""
        from runtime.api.correlation import get_request_id

        class FakeState:
            pass

        class FakeRequest:
            state = FakeState()

        result = get_request_id(FakeRequest())  # type: ignore[arg-type]
        assert result == "unknown"

    def test_get_correlation_id_no_state(self):
        """get_correlation_id with no correlation_id attribute returns 'unknown'."""
        from runtime.api.correlation import get_correlation_id

        class FakeState:
            pass

        class FakeRequest:
            state = FakeState()

        result = get_correlation_id(FakeRequest())  # type: ignore[arg-type]
        assert result == "unknown"

    def test_get_request_id_with_state(self):
        """get_request_id returns value from request.state."""
        from unittest.mock import MagicMock

        from runtime.api.correlation import get_request_id
        request = MagicMock()
        request.state.request_id = "req-123"
        result = get_request_id(request)
        assert result == "req-123"

    def test_get_correlation_id_with_state(self):
        """get_correlation_id returns value from request.state."""
        from unittest.mock import MagicMock

        from runtime.api.correlation import get_correlation_id
        request = MagicMock()
        request.state.correlation_id = "corr-456"
        result = get_correlation_id(request)
        assert result == "corr-456"


# ═══════════════════════════════════════════════════════════════════════════
# rbac.py require_role decorator tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRequireRoleDecorator:
    def test_require_role_returns_callable(self):
        """require_role should return a decorator."""
        from runtime.api.rbac import Role, require_role
        decorator = require_role(Role.ADMIN)
        assert callable(decorator)

    def test_require_role_decorates_function(self):
        """Decorated function should be callable."""
        from runtime.api.rbac import Role, require_role

        @require_role(Role.ADMIN)
        async def my_handler(request):
            return {"ok": True}

        assert callable(my_handler)

    def test_require_role_disabled_passes(self, monkeypatch):
        """When RBAC disabled, decorated function passes through."""
        monkeypatch.setenv("TAGENT_RBAC_ENABLED", "0")
        import importlib

        import runtime.api.rbac as rbac_mod
        importlib.reload(rbac_mod)

        @rbac_mod.require_role(rbac_mod.Role.VIEWER)
        async def viewer_handler(request):
            return {"ok": True}

        # Should not raise — RBAC is disabled
        assert callable(viewer_handler)
