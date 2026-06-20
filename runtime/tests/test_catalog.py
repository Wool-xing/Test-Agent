"""Verify catalog registry returns correct counts."""

from __future__ import annotations

from runtime.api.deps import Kernel


def test_catalog_experts_count():
    """Catalog should return exactly 16 experts."""
    k = Kernel()
    data = k.catalog()
    assert data["counts"]["experts"] == 16, f"expected 16 experts, got {data['counts']['experts']}"


def test_catalog_skills_count():
    """Catalog should return 30-32 skills (30 active + up to 2 vision)."""
    k = Kernel()
    data = k.catalog()
    count = data["counts"]["skills"]
    assert 35 <= count <= 45, f"expected 35-45 skills, got {count}"


def test_catalog_experts_have_required_fields():
    """Every expert entry has kind/name/description."""
    k = Kernel()
    data = k.catalog()
    for e in data["experts"]:
        assert "kind" in e
        assert "name" in e
        assert "description" in e
        assert e["kind"] == "expert"


def test_catalog_skills_have_required_fields():
    """Every skill entry has kind/name/description."""
    k = Kernel()
    data = k.catalog()
    for s in data["skills"]:
        assert "kind" in s
        assert "name" in s
        assert "description" in s
        assert s["kind"] == "skill"


def test_catalog_includes_test_lead():
    """test-lead must be in the expert list."""
    k = Kernel()
    data = k.catalog()
    names = [e["name"] for e in data["experts"]]
    assert "test-lead" in names
