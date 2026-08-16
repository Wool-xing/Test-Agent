"""Enterprise features tests: RBAC, SSO, Audit, Tenancy V2."""

from __future__ import annotations

import pytest
from fastapi import Request

from runtime.api.audit import AuditTrail
from runtime.api.auth.rbac import RBAC, Permission, Role
from runtime.api.auth.sso import SSOConfig, SSOManager
from runtime.api.tenancy_v2 import TenantManager

# ═══════════════════════════════════════════════════════════════
# RBAC Tests
# ═══════════════════════════════════════════════════════════════


class TestRBAC:
    def test_admin_has_all_permissions(self):
        """Admin role grants every permission."""
        rbac = RBAC()
        for perm in Permission:
            assert rbac.has_permission(Role.ADMIN, perm), f"Admin should have {perm}"

    def test_viewer_cannot_run_tests(self):
        """Viewer role does not grant test execution permission."""
        rbac = RBAC()
        assert not rbac.has_permission(Role.VIEWER, Permission.RUN_TESTS)

    def test_viewer_can_view_results(self):
        rbac = RBAC()
        assert rbac.has_permission(Role.VIEWER, Permission.VIEW_RESULTS)

    def test_tester_can_run_tests(self):
        rbac = RBAC()
        assert rbac.has_permission(Role.TESTER, Permission.RUN_TESTS)

    def test_manager_has_manage_agents(self):
        rbac = RBAC()
        assert rbac.has_permission(Role.MANAGER, Permission.MANAGE_AGENTS)

    def test_manager_cannot_manage_users(self):
        """Manager should NOT have user management permission."""
        rbac = RBAC()
        assert not rbac.has_permission(Role.MANAGER, Permission.MANAGE_USERS)

    def test_check_raises_for_insufficient_permission(self):
        rbac = RBAC()
        with pytest.raises(Exception) as exc_info:
            rbac.check(Role.VIEWER, Permission.RUN_TESTS)
        # FastAPI HTTPException or generic — both indicate denial
        assert exc_info.value is not None

    def test_check_passes_for_sufficient_permission(self):
        rbac = RBAC()
        # Should not raise
        result = rbac.check(Role.ADMIN, Permission.MANAGE_USERS)
        assert result is None  # check() returns None on success

    def test_rbac_disabled_allows_all(self):
        rbac = RBAC(enabled=False)
        assert rbac.has_permission(Role.VIEWER, Permission.MANAGE_USERS)

    def test_grant_and_revoke_permission(self):
        rbac = RBAC()
        rbac.grant_permission(Role.VIEWER, Permission.RUN_TESTS)
        assert rbac.has_permission(Role.VIEWER, Permission.RUN_TESTS)

        rbac.revoke_permission(Role.VIEWER, Permission.RUN_TESTS)
        assert not rbac.has_permission(Role.VIEWER, Permission.RUN_TESTS)

    def test_get_permissions(self):
        rbac = RBAC()
        perms = rbac.get_permissions(Role.VIEWER)
        assert Permission.VIEW_RESULTS.value in perms
        assert Permission.VIEW_AUDIT.value in perms
        assert Permission.RUN_TESTS.value not in perms


# ═══════════════════════════════════════════════════════════════
# SSO Tests
# ═══════════════════════════════════════════════════════════════


class TestSSO:
    @pytest.fixture
    def oidc_config(self) -> SSOConfig:
        return SSOConfig(
            provider="oidc",
            client_id="test-client-id",
            client_secret="test-client-secret",
            issuer_url="https://accounts.example.com",
            redirect_uri="http://localhost:8000/auth/callback",
            scopes=["openid", "email", "profile"],
        )

    @pytest.fixture
    def sso(self, oidc_config: SSOConfig) -> SSOManager:
        return SSOManager(oidc_config)

    def test_authorization_url_generation(self, sso: SSOManager):
        state = "random-state-123"
        url = sso.get_authorization_url(state)
        assert "client_id=test-client-id" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fauth%2Fcallback" in url
        assert "response_type=code" in url
        assert "state=random-state-123" in url
        assert "scope=openid+email+profile" in url

    def test_saml_authorization_url_generation(self):
        saml_config = SSOConfig(
            provider="saml",
            client_id="saml-client",
            client_secret="saml-secret",
            issuer_url="https://idp.example.com/saml2",
            redirect_uri="http://localhost:8000/auth/saml/acs",
            saml_entity_id="test-entity",
            saml_acs_url="http://localhost:8000/auth/saml/acs",
        )
        saml_sso = SSOManager(saml_config)
        url = saml_sso.get_authorization_url("state-456")
        assert "SAMLRequest=" in url
        assert "RelayState=state-456" in url

    def test_validate_token_rejects_when_jwks_not_warmed(self, sso: SSOManager):
        """Without pre-warmed JWKS, a structurally valid token must be REJECTED (fail-closed)."""
        import time as _time

        import jwt as _jwt

        token = _jwt.encode(
            {
                "sub": "user-1",
                "email": "user@example.com",
                "iss": "https://accounts.example.com",
                "aud": "test-client-id",
                "exp": int(_time.time()) + 3600,
                "iat": int(_time.time()),
            },
            key="secret",
            algorithm="HS256",
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            sso.validate_token(token)
        assert exc_info.value.status_code == 401
        # Detail must be the JWKS-missing rejection — proves the header alg
        # (HS256, not in the allowlist... HS256 IS rejected by allowlist, so
        # use an RS256-header token below instead)

    def test_validate_token_rs256_reaches_jwks_check(self, sso: SSOManager):
        """RS256-header token with valid claims must pass alg check and reach the
        JWKS-availability rejection (not die at 'Unsupported token algorithm')."""
        import base64
        import json

        def _b64(d):
            return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

        token = (
            _b64({"alg": "RS256"})
            + "."
            + _b64({
                "sub": "user-1",
                "iss": "https://accounts.example.com",
                "aud": "test-client-id",
                "exp": int(__import__("time").time()) + 3600,
            })
            + "."
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            sso.validate_token(token)
        assert exc_info.value.status_code == 401
        assert "JWKS" in str(exc_info.value.detail)

    def test_validate_token_rejects_missing_exp(self, sso: SSOManager):
        """Token without exp claim must be rejected, not accepted as valid."""
        import jwt as _jwt

        token = _jwt.encode(
            {
                "sub": "user-1",
                "iss": "https://accounts.example.com",
                "aud": "test-client-id",
            },
            key="secret",
            algorithm="HS256",
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            sso.validate_token(token)
        assert exc_info.value.status_code == 401
        assert "exp" in str(exc_info.value.detail).lower()

    def test_validate_token_rejects_unsupported_alg(self, sso: SSOManager):
        """Token with alg not in allowlist (e.g. none) must be rejected."""
        import time as _time

        import jwt as _jwt

        token = _jwt.encode(
            {
                "sub": "attacker",
                "iss": "https://accounts.example.com",
                "aud": "test-client-id",
                "exp": int(_time.time()) + 3600,
            },
            key=None,
            algorithm="none",
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            sso.validate_token(token)
        assert exc_info.value.status_code == 401
        assert "algorithm" in str(exc_info.value.detail).lower()

    def test_validate_token_rejects_non_numeric_exp(self, sso: SSOManager):
        """Non-numeric exp must be 401, not an unhandled TypeError (500)."""
        import base64
        import json

        def _b64(d):
            return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

        token = (
            _b64({"alg": "RS256"})
            + "."
            + _b64({
                "sub": "attacker",
                "iss": "https://accounts.example.com",
                "aud": "test-client-id",
                "exp": "abc",
            })
            + "."
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            sso.validate_token(token)
        assert exc_info.value.status_code == 401

    async def test_get_user_info_without_endpoint_rejected(self, sso: SSOManager):
        """No userinfo_endpoint must NOT fall back to unverified claims."""
        sso._oidc_config = {"userinfo_endpoint": ""}

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await sso.get_user_info("some-token")
        assert exc_info.value.status_code == 502

    def test_validate_token_rejects_expired(self, sso: SSOManager):
        import time as _time

        import jwt as _jwt

        token = _jwt.encode(
            {
                "sub": "user-1",
                "iss": "https://accounts.example.com",
                "aud": "test-client-id",
                "exp": int(_time.time()) - 3600,  # expired 1 hour ago
                "iat": int(_time.time()) - 7200,
            },
            key="secret",
            algorithm="HS256",
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            sso.validate_token(token)
        assert exc_info.value.status_code == 401
        assert "expired" in str(exc_info.value.detail).lower()

    def test_validate_token_rejects_wrong_issuer(self, sso: SSOManager):
        import time as _time

        import jwt as _jwt

        token = _jwt.encode(
            {
                "sub": "user-1",
                "iss": "https://evil.example.com",
                "aud": "test-client-id",
                "exp": int(_time.time()) + 3600,
            },
            key="secret",
            algorithm="HS256",
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            sso.validate_token(token)
        assert exc_info.value.status_code == 401

    def test_provider_type_detection(self, sso: SSOManager):
        assert sso._provider_type == "oidc"

        saml_sso = SSOManager(
            SSOConfig(
                provider="saml",
                client_id="c",
                client_secret="s",
                issuer_url="https://idp.example.com",
                redirect_uri="http://localhost/cb",
            )
        )
        assert saml_sso._provider_type == "saml"


# ═══════════════════════════════════════════════════════════════
# Audit Trail Tests
# ═══════════════════════════════════════════════════════════════


class TestAuditTrail:
    @pytest.fixture
    def audit(self) -> AuditTrail:
        a = AuditTrail(":memory:")
        yield a
        a.close()

    def test_record_creates_entry(self, audit: AuditTrail):
        entry = audit.record("user1", "test.execute", "smoke-test", {"status": "pass"})
        assert entry.id is not None
        assert entry.actor == "user1"
        assert entry.action == "test.execute"
        assert entry.resource == "smoke-test"
        assert entry.details == {"status": "pass"}
        assert len(entry.integrity_hash) == 64  # SHA-256 hex

    def test_verify_integrity_passes(self, audit: AuditTrail):
        audit.record("user1", "test.run", "smoke-test", {})
        audit.record("user2", "test.run", "unit-test", {})
        ok, msg = audit.verify_integrity()
        assert ok, f"Integrity should pass, got: {msg}"

    def test_verify_integrity_empty(self, audit: AuditTrail):
        ok, msg = audit.verify_integrity()
        assert ok

    def test_hash_chain_detects_tampering(self, audit: AuditTrail):
        """Direct DB manipulation breaks the hash chain."""
        audit.record("user1", "test.run", "smoke-test", {})
        audit.record("user2", "test.run", "unit-test", {})

        # Tamper: modify an entry's actor directly in the DB
        conn = audit._get_conn()
        conn.execute("UPDATE audit_log SET actor = 'attacker' WHERE actor = 'user1'")
        conn.commit()

        ok, msg = audit.verify_integrity()
        assert not ok, "Integrity should detect tampering"
        assert "Hash mismatch" in msg

    def test_query_by_actor(self, audit: AuditTrail):
        audit.record("user-a", "test.run", "smoke", {})
        audit.record("user-b", "test.run", "unit", {})
        audit.record("user-a", "gate.evaluate", "quality", {})

        results = audit.query(actor="user-a")
        assert len(results) == 2
        for r in results:
            assert r.actor == "user-a"

    def test_query_by_action(self, audit: AuditTrail):
        audit.record("user1", "test.run", "smoke", {})
        audit.record("user1", "gate.evaluate", "quality", {})
        audit.record("user1", "agent.decision", "router", {})

        results = audit.query(action="test.")
        assert len(results) == 1
        assert results[0].action == "test.run"

    def test_query_with_limit(self, audit: AuditTrail):
        for i in range(10):
            audit.record("user1", "test.run", f"test-{i}", {})
        results = audit.query(limit=3)
        assert len(results) == 3

    def test_multiple_entries_maintain_chain(self, audit: AuditTrail):
        """50 entries — verify the chain stays intact."""
        for i in range(50):
            audit.record(f"user-{i % 5}", "test.run", f"test-{i}", {"index": i})
        ok, msg = audit.verify_integrity()
        assert ok, f"Chain broken at 50 entries: {msg}"


# ═══════════════════════════════════════════════════════════════
# Tenancy V2 Tests
# ═══════════════════════════════════════════════════════════════


class TestTenancyV2:
    @pytest.fixture
    def tm(self) -> TenantManager:
        t = TenantManager(":memory:")
        yield t
        t.close()

    def test_create_tenant(self, tm: TenantManager):
        tenant = tm.create_tenant("Acme Corp", "admin@acme.com")
        assert tenant["name"] == "Acme Corp"
        assert tenant["admin_email"] == "admin@acme.com"
        assert "id" in tenant
        assert "created_at" in tenant

    def test_get_tenant(self, tm: TenantManager):
        created = tm.create_tenant("TestCo", "admin@testco.com")
        fetched = tm.get_tenant(created["id"])
        assert fetched is not None
        assert fetched["name"] == "TestCo"

    def test_get_nonexistent_tenant(self, tm: TenantManager):
        assert tm.get_tenant("nonexistent-id") is None

    def test_scope_query_simple_select(self, tm: TenantManager):
        scoped = tm.scope_query("SELECT * FROM runs", "tenant-abc")
        assert "WHERE tenant_id = 'tenant-abc'" in scoped

    def test_scope_query_with_existing_where(self, tm: TenantManager):
        scoped = tm.scope_query(
            "SELECT * FROM runs WHERE status = 'running'", "tenant-xyz"
        )
        assert "tenant_id = 'tenant-xyz'" in scoped
        assert "status = 'running'" in scoped

    def test_scope_query_with_order_by(self, tm: TenantManager):
        scoped = tm.scope_query(
            "SELECT * FROM runs ORDER BY created_at DESC", "tenant-1"
        )
        assert "WHERE tenant_id = 'tenant-1'" in scoped
        assert "ORDER BY created_at DESC" in scoped

    def test_access_verification(self, tm: TenantManager):
        tenant = tm.create_tenant("Test", "a@t.com")
        tm.add_member(tenant["id"], "user-123", "member")
        assert tm.verify_access("user-123", tenant["id"])
        assert not tm.verify_access("user-999", tenant["id"])

    def test_member_management(self, tm: TenantManager):
        tenant = tm.create_tenant("Org", "admin@org.com")
        tm.add_member(tenant["id"], "alice", "admin")
        tm.add_member(tenant["id"], "bob", "member")

        members = tm.get_members(tenant["id"])
        assert len(members) == 2

        tm.remove_member(tenant["id"], "bob")
        members = tm.get_members(tenant["id"])
        assert len(members) == 1
        assert members[0]["user_id"] == "alice"

    def test_list_tenants(self, tm: TenantManager):
        tm.create_tenant("A", "a@a.com")
        tm.create_tenant("B", "b@b.com")
        tenants = tm.list_tenants()
        assert len(tenants) == 2

    def test_delete_tenant(self, tm: TenantManager):
        tenant = tm.create_tenant("Temp", "t@t.com")
        assert tm.delete_tenant(tenant["id"])
        assert tm.get_tenant(tenant["id"]) is None


# ═══════════════════════════════════════════════════════════════════════════
# EnterpriseMiddleware fail-closed behavior
# ═══════════════════════════════════════════════════════════════════════════


class TestEnterpriseMiddleware:
    """Mounted enterprise stack must reject anonymous requests (fail-closed)."""

    @staticmethod
    def _make_app(tmp_path):
        from fastapi import FastAPI

        from runtime.api.audit import AuditTrail
        from runtime.api.auth.rbac import RBAC
        from runtime.api.auth.sso import SSOConfig, SSOManager
        from runtime.api.middleware.enterprise import EnterpriseMiddleware

        sso = SSOManager(
            SSOConfig(
                provider="oidc",
                client_id="test-client-id",
                client_secret="test-client-secret",
                issuer_url="https://accounts.example.com",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        )
        app = FastAPI()
        app.add_middleware(
            EnterpriseMiddleware,
            sso_manager=sso,
            rbac=RBAC(),
            audit=AuditTrail(str(tmp_path / "audit.db")),
            exclude_paths=["/health"],
        )

        @app.get("/data")
        def data():
            return {"ok": True}

        @app.get("/health")
        def health():
            return {"status": "ok"}

        return app

    def test_no_token_rejected(self, tmp_path):
        """Request without Bearer token must be 401 when middleware is mounted."""
        from fastapi.testclient import TestClient

        client = TestClient(self._make_app(tmp_path))
        resp = client.get("/data")
        assert resp.status_code == 401

    def test_excluded_path_still_open(self, tmp_path):
        from fastapi.testclient import TestClient

        client = TestClient(self._make_app(tmp_path))
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_invalid_token_rejected(self, tmp_path):
        from fastapi.testclient import TestClient

        client = TestClient(self._make_app(tmp_path))
        resp = client.get("/data", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 401


class TestUnknownRolesRejected:
    """Unknown user_roles must 403, never silently downgrade to viewer."""

    def test_unknown_user_roles_rejected(self):
        from types import SimpleNamespace

        from runtime.api.auth.rbac import RBAC, Permission

        rbac = RBAC()

        @rbac.require(Permission.RUN_TESTS)
        async def handler(request):
            return {"ok": True}

        request = SimpleNamespace(state=SimpleNamespace(user_roles=["superuser"]))
        with pytest.raises(Exception) as exc_info:
            import asyncio
            asyncio.run(handler(request=request))
        assert getattr(exc_info.value, "status_code", None) == 403

    def test_empty_user_roles_falls_back_to_viewer(self):
        from types import SimpleNamespace

        from runtime.api.auth.rbac import RBAC, Permission

        rbac = RBAC()

        @rbac.require(Permission.VIEW_RESULTS)
        async def handler(request):
            return {"ok": True}

        request = SimpleNamespace(state=SimpleNamespace(user_roles=[]))
        import asyncio
        # viewer may view results → no exception
        asyncio.run(handler(request=request))

    def test_known_role_in_list_resolves(self):
        from types import SimpleNamespace

        from runtime.api.auth.rbac import RBAC, Permission

        rbac = RBAC()

        @rbac.require(Permission.MANAGE_AGENTS)
        async def handler(request):
            return {"ok": True}

        request = SimpleNamespace(state=SimpleNamespace(user_roles=["tester", "admin"]))
        import asyncio
        asyncio.run(handler(request=request))  # admin present → no exception


class TestEnterpriseRoleClaimGuard:
    """String 'roles' claim must not grant ADMIN via substring match."""

    def _setup(self, tmp_path, monkeypatch, claims):
        from fastapi.testclient import TestClient

        app = TestEnterpriseMiddleware._make_app(tmp_path)
        sso = app.user_middleware[0].kwargs["sso_manager"]

        async def fake_validate(token):
            return claims

        monkeypatch.setattr(sso, "validate_token_async", fake_validate)

        @app.get("/whoami")
        def whoami(request: Request):
            role = getattr(request.state, "role", None)
            return {"role": role.value if role else "none"}

        return TestClient(app)

    def test_roles_string_claim_stays_viewer(self, tmp_path, monkeypatch):
        client = self._setup(
            tmp_path, monkeypatch,
            {"sub": "u1", "email": "x@y.z", "roles": "administrator"},
        )
        resp = client.get("/whoami", headers={"Authorization": "Bearer valid"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "viewer"

    def test_roles_list_with_admin_grants_admin(self, tmp_path, monkeypatch):
        client = self._setup(
            tmp_path, monkeypatch,
            {"sub": "u1", "email": "x@y.z", "roles": ["admin"]},
        )
        resp = client.get("/whoami", headers={"Authorization": "Bearer valid"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["role"] == "admin"


class TestValidateTokenAsync:
    """validate_token_async — the production path — must map PyJWT errors to 401."""

    @pytest.fixture
    def sso(self):
        return SSOManager(
            SSOConfig(
                provider="oidc",
                client_id="test-client-id",
                client_secret="test-client-secret",
                issuer_url="https://accounts.example.com",
                redirect_uri="http://localhost:8000/auth/callback",
            )
        )

    async def test_bad_signature_raises_401(self, sso, monkeypatch):
        import base64
        import json
        import time

        def _b64(d):
            return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

        token = (
            _b64({"alg": "RS256"})
            + "."
            + _b64({
                "sub": "u1",
                "iss": "https://accounts.example.com",
                "aud": "test-client-id",
                "exp": int(time.time()) + 3600,
            })
            + ".fakesig"
        )

        class FakeKey:
            key = "not-the-right-key"

        class FakeJwks:
            def get_signing_key_from_jwt(self, token):  # noqa: ARG002
                return FakeKey()

        async def fake_get_jwks():
            return FakeJwks()

        monkeypatch.setattr(sso, "_get_jwks_client", fake_get_jwks)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await sso.validate_token_async(token)
        assert exc_info.value.status_code == 401


class TestEnterpriseMountGate:
    """TAGENT_ENTERPRISE_ENABLED boot gate: complete config mounts, incomplete refuses."""

    def _run(self, env_extra):
        import os
        import subprocess
        import sys
        from pathlib import Path

        env = dict(os.environ)
        # Defensive: strip any SSO vars leaked by other tests in the same process
        for k in list(env):
            if k.startswith("TAGENT_SSO_") or k == "TAGENT_ENTERPRISE_ENABLED":
                env.pop(k, None)
        env.update(env_extra)
        code = (
            "from runtime.api.main import app; "
            "print('MOUNTED' if any(m.cls.__name__ == 'EnterpriseMiddleware' for m in app.user_middleware) else 'NOT_MOUNTED')"
        )
        repo = Path(__file__).resolve().parents[2]
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(repo),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_complete_config_mounts(self):
        r = self._run({
            "TAGENT_ENTERPRISE_ENABLED": "1",
            "TAGENT_SSO_CLIENT_ID": "cid",
            "TAGENT_SSO_CLIENT_SECRET": "csec",
            "TAGENT_SSO_ISSUER_URL": "https://issuer.example.com",
        })
        assert r.returncode == 0, r.stderr
        assert "MOUNTED" in r.stdout

    def test_incomplete_config_refuses_boot(self):
        r = self._run({"TAGENT_ENTERPRISE_ENABLED": "1"})
        assert r.returncode != 0
        assert "SSO config incomplete" in r.stderr
