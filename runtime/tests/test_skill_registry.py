"""TDD: Skill registry — extended discovery from local SDK directory.

Sprint 3: Skill registration and discovery mechanism.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sdk_registry_dir(tmp_path):
    """Create a local SDK registry with one installed skill."""
    reg = tmp_path / "skills"
    reg.mkdir()
    skill_dir = reg / "my-check"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("""---
name: my-check
version: 1.0.0
display_name: My Check
description: Test skill from SDK registry
permissions:
  network: none
  filesystem: read
  shell: none
  timeout: 30
---
# My Check
""", encoding="utf-8")
    return reg


class TestSkillDiscovery:
    """Skill discovery from multiple sources."""

    def test_discover_builtin_skills(self):
        """Built-in skills from ai/skills/ should be discoverable."""
        from runtime.registry.registry import build_catalog
        cat = build_catalog()
        assert len(cat.skills) >= 5
        assert "ping-check" in cat.skills or "ping_check" in cat.skills

    def test_discover_sdk_registry_skills(self, sdk_registry_dir):
        """Skills from SDK local registry should be discoverable."""
        from runtime.sdk.discovery import discover_skills
        skills = discover_skills(sdk_registry_dir)
        assert len(skills) >= 1
        names = [s["name"] for s in skills]
        assert "my-check" in names

    def test_discover_empty_registry(self, tmp_path):
        """Empty registry should return empty list."""
        from runtime.sdk.discovery import discover_skills
        empty = tmp_path / "empty"
        empty.mkdir()
        skills = discover_skills(empty)
        assert skills == []

    def test_skill_metadata_complete(self, sdk_registry_dir):
        """Discovered skills should have complete metadata."""
        from runtime.sdk.discovery import discover_skills
        skills = discover_skills(sdk_registry_dir)
        s = skills[0]
        assert s["name"] == "my-check"
        assert s["version"] == "1.0.0"
        assert "permissions" in s


class TestRegistryIntegration:
    """Integration: catalog includes SDK registry skills."""

    def test_catalog_includes_sdk_skills(self, sdk_registry_dir):
        """build_catalog should merge SDK registry skills."""
        from runtime.registry.registry import build_catalog
        cat = build_catalog(extra_skill_dirs=[sdk_registry_dir])
        assert "my-check" in cat.skills
