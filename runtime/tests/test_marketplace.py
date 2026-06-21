"""TDD: Local skill marketplace (Sprint 3)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def marketplace_dir(tmp_path):
    mp = tmp_path / "marketplace"
    mp.mkdir()
    return mp


@pytest.fixture
def sample_package(tmp_path):
    pkg = tmp_path / "test-skill.tar.gz"
    pkg.write_bytes(b"fake-tar-gz-content")
    return pkg


class TestMarketplacePublish:
    def test_publish_adds_to_index(self, sample_package, marketplace_dir):
        from runtime.sdk.marketplace import publish_to_marketplace, _load_index
        result = publish_to_marketplace(sample_package, marketplace_dir)
        assert result.ok is True
        data = _load_index(marketplace_dir)
        assert len(data["skills"]) >= 1
        assert data["skills"][0]["name"] == "test-skill"

    def test_publish_duplicate_fails(self, sample_package, marketplace_dir):
        from runtime.sdk.marketplace import publish_to_marketplace
        publish_to_marketplace(sample_package, marketplace_dir)
        result = publish_to_marketplace(sample_package, marketplace_dir)
        assert result.ok is False
        assert "already exists" in result.error

    def test_publish_missing_package_fails(self, marketplace_dir):
        from runtime.sdk.marketplace import publish_to_marketplace
        result = publish_to_marketplace(Path("/nonexistent/pkg.tar.gz"), marketplace_dir)
        assert result.ok is False


class TestMarketplaceSearch:
    def test_search_finds_by_name(self, sample_package, marketplace_dir):
        from runtime.sdk.marketplace import publish_to_marketplace, search_marketplace
        publish_to_marketplace(sample_package, marketplace_dir)
        result = search_marketplace("test", marketplace_dir)
        assert result.ok is True
        assert len(result.entries) >= 1

    def test_search_empty_returns_empty(self, marketplace_dir):
        from runtime.sdk.marketplace import search_marketplace
        result = search_marketplace("nonexistent", marketplace_dir)
        assert result.ok is True
        assert result.entries == []


class TestMarketplaceList:
    def test_list_returns_published(self, sample_package, marketplace_dir):
        from runtime.sdk.marketplace import publish_to_marketplace, list_marketplace
        publish_to_marketplace(sample_package, marketplace_dir)
        result = list_marketplace(marketplace_dir)
        assert result.ok is True
        assert len(result.entries) >= 1
