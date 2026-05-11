"""Smoke test: registry scans existing experts + skills."""

from __future__ import annotations

from runtime.registry.registry import build_catalog


def test_catalog_loads_existing_assets():
    cat = build_catalog()
    # Project charter: 14 experts + 13 skills baseline.
    assert len(cat.experts) >= 14, f"experts loaded={len(cat.experts)}, expect >=14"
    assert len(cat.skills) >= 13, f"skills loaded={len(cat.skills)}, expect >=13"
    assert "test-lead" in cat.experts, "test-lead expert missing"


def test_catalog_entries_have_description():
    cat = build_catalog()
    for entry in cat.all():
        assert entry.description, f"{entry.name} missing description"


def test_lookup_returns_entry():
    cat = build_catalog()
    e = cat.lookup("test-lead")
    assert e is not None
    assert e.kind == "expert"
