"""Test marketplace API endpoints."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from runtime.api.main import app
from runtime.marketplace.catalog import Entry, save_local

client = TestClient(app)


def _seed_registry(entries: list[Entry], monkeypatch) -> None:
    """Seed registry.json with test entries for the duration of the test."""
    from pathlib import Path
    import tempfile

    data = {
        "_comment": "test seed",
        "version": "1.0",
        "last_updated": "2026-01-01",
        "entries": [
            {
                "name": e.name,
                "version": e.version,
                "lane": e.lane,
                "source_url": e.source_url,
                "sha256": e.sha256,
                "signature": e.signature,
                "license": e.license,
                "safety_score": e.safety_score,
                "confidence": e.confidence,
                "source_tier": e.source_tier,
                "installed_at": e.installed_at,
                "tags": e.tags,
            }
            for e in entries
        ],
    }

    # Write to temp file, then monkeypatch _registry_path
    tmp = Path(tempfile.mktemp(suffix=".json"))
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    import runtime.marketplace.catalog as cat

    monkeypatch.setattr(cat, "_registry_path", lambda: tmp)


def test_list_plugins_returns_empty_by_default():
    """Without seeded data, /api/marketplace/plugins returns empty list."""
    resp = client.get("/api/marketplace/plugins")
    assert resp.status_code == 200
    data = resp.json()
    assert "plugins" in data
    assert isinstance(data["plugins"], list)


def test_list_plugins_with_seeded_data(monkeypatch):
    """With seeded entries, /api/marketplace/plugins returns them enriched."""
    entries = [
        Entry(name="hello-world", version="1.0.0", lane="skills", source_url="https://example.com/hello", tags=["test"]),
        Entry(name="code-reviewer", version="2.1.0", lane="agents", source_url="https://example.com/cr", license="MIT", safety_score=85, tags=["ai", "code"]),
    ]
    _seed_registry(entries, monkeypatch)

    resp = client.get("/api/marketplace/plugins")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    names = [p["name"] for p in data["plugins"]]
    assert "hello-world" in names
    assert "code-reviewer" in names

    # Check enrichment
    hello = next(p for p in data["plugins"] if p["name"] == "hello-world")
    assert hello["plugin_type"] == "skill"
    assert hello["version"] == "1.0.0"


def test_list_plugins_filter_by_type(monkeypatch):
    """Filter plugins by plugin_type query parameter."""
    entries = [
        Entry(name="skill-a", version="1.0.0", lane="skills", source_url="https://a.example", tags=[]),
        Entry(name="agent-b", version="1.0.0", lane="agents", source_url="https://b.example", tags=[]),
    ]
    _seed_registry(entries, monkeypatch)

    resp = client.get("/api/marketplace/plugins?type=agent")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["plugins"][0]["name"] == "agent-b"


def test_search_plugins_by_keyword(monkeypatch):
    """Search endpoint finds plugins by name or tag."""
    entries = [
        Entry(name="python-lint", version="1.0.0", lane="skills", source_url="https://x.example", tags=["linting", "python"]),
        Entry(name="go-fmt", version="1.0.0", lane="skills", source_url="https://y.example", tags=["formatting", "go"]),
    ]
    _seed_registry(entries, monkeypatch)

    resp = client.get("/api/marketplace/search?q=python")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["plugins"][0]["name"] == "python-lint"


def test_plugin_detail_404_for_missing():
    """Non-existent plugin returns 404."""
    resp = client.get("/api/marketplace/plugins/nonexistent-plugin-xyz")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]
