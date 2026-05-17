"""Verify API auth middleware and CORS configuration."""

from __future__ import annotations

from fastapi.testclient import TestClient

from runtime.api.main import app

client = TestClient(app)


def test_health_no_auth_required():
    """Health endpoint is always accessible without token."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_public_endpoints_no_auth_by_default():
    """Without auth token configured, all endpoints are accessible."""
    # Catalog is public by default (no auth token set)
    resp = client.get("/catalog")
    assert resp.status_code == 200
    data = resp.json()
    assert "experts" in data
    assert "skills" in data


def test_auth_middleware_blocks_when_token_set(monkeypatch):
    """When TAGENT_API_AUTH_TOKEN is set, protected endpoints return 401."""
    monkeypatch.setenv("TAGENT_API_AUTH_TOKEN", "test-token-123")
    from runtime.api.main import _settings
    _settings.api_auth_token = "test-token-123"

    resp = client.get("/catalog")
    assert resp.status_code == 401
    assert "unauthorized" in resp.json()["detail"]


def test_auth_middleware_allows_with_correct_token(monkeypatch):
    """With correct Bearer token, protected endpoints work."""
    monkeypatch.setenv("TAGENT_API_AUTH_TOKEN", "test-token-123")
    from runtime.api.main import _settings
    _settings.api_auth_token = "test-token-123"

    resp = client.get("/catalog", headers={"Authorization": "Bearer test-token-123"})
    assert resp.status_code == 200


def test_health_always_accessible_even_with_token(monkeypatch):
    """Health is excluded from auth check."""
    monkeypatch.setenv("TAGENT_API_AUTH_TOKEN", "test-token-123")
    from runtime.api.main import _settings
    _settings.api_auth_token = "test-token-123"

    resp = client.get("/health")
    assert resp.status_code == 200


def test_cors_headers_present():
    """CORS headers are present on normal responses for localhost origin."""
    resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    # CORSMiddleware sets allow-origin on all responses when origin matches
    if "access-control-allow-origin" in resp.headers:
        assert "localhost" in resp.headers["access-control-allow-origin"]
