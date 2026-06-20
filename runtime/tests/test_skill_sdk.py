"""TDD: Skill SDK — create, validate, package, publish Skill.

Sprint 3 requirement: developer can create a Skill → test locally → publish within 30 minutes.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def temp_skill_dir():
    """Create a temporary skill directory with minimal SKILL.md."""
    d = Path(tempfile.mkdtemp(prefix="test-skill-"))
    skill_md = d / "SKILL.md"
    skill_md.write_text("""---
name: test-skill
version: 1.0.0
display_name: Test Skill
description: A test skill for SDK unit tests
permissions:
  network: none
  filesystem: read
  shell: none
  timeout: 30
---

# Test Skill

## Overview
Test skill for SDK validation.
""", encoding="utf-8")
    return d


# ── Test Skill Creation ─────────────────────────────────────────────


class TestSkillCreate:
    """4.X.2: Skill creation via SDK scaffold."""

    def test_scaffold_creates_directory(self, tmp_path):
        """scaffold should create skill directory with SKILL.md template."""
        from runtime.sdk.scaffold import scaffold_skill
        skill_dir = scaffold_skill("my-test-skill", base_dir=tmp_path)
        assert skill_dir.exists()
        assert skill_dir.is_dir()
        assert (skill_dir / "SKILL.md").exists()

    def test_scaffold_generates_valid_frontmatter(self, tmp_path):
        """Generated SKILL.md must have valid YAML frontmatter."""
        from runtime.sdk.scaffold import scaffold_skill
        import yaml
        skill_dir = scaffold_skill("valid-skill", base_dir=tmp_path)
        content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert content.startswith("---")
        parts = content.split("---")
        assert len(parts) >= 3
        meta = yaml.safe_load(parts[1])
        assert meta["name"] == "valid-skill"
        assert meta["version"] == "0.1.0"
        assert "permissions" in meta

    def test_scaffold_rejects_invalid_name(self, tmp_path):
        """Skill name must be kebab-case, reject invalid names."""
        from runtime.sdk.scaffold import scaffold_skill
        with pytest.raises(ValueError, match="kebab-case"):
            scaffold_skill("Invalid Name", base_dir=tmp_path)
        with pytest.raises(ValueError, match="kebab-case"):
            scaffold_skill("UPPERCASE", base_dir=tmp_path)

    def test_scaffold_creates_executor_stub(self, tmp_path):
        """Scaffold should generate executor.py stub."""
        from runtime.sdk.scaffold import scaffold_skill
        skill_dir = scaffold_skill("stub-skill", base_dir=tmp_path)
        executor = skill_dir / "executor.py"
        assert executor.exists()
        content = executor.read_text(encoding="utf-8")
        assert "def execute" in content


# ── Test Skill Validation ───────────────────────────────────────────


class TestSkillValidate:
    """4.X.2: Skill validation before packaging."""

    def test_valid_skill_passes(self, temp_skill_dir):
        """A well-formed SKILL.md should pass validation."""
        from runtime.sdk.validate import validate_skill
        result = validate_skill(temp_skill_dir)
        assert result.ok
        assert len(result.errors) == 0

    def test_missing_skill_md_fails(self, tmp_path):
        """Directory without SKILL.md should fail validation."""
        from runtime.sdk.validate import validate_skill
        d = tmp_path / "empty"
        d.mkdir()
        result = validate_skill(d)
        assert not result.ok
        assert any("SKILL.md" in e for e in result.errors)

    def test_missing_required_field_fails(self, tmp_path):
        """SKILL.md missing required fields should fail."""
        from runtime.sdk.validate import validate_skill
        d = tmp_path / "bad-skill"
        d.mkdir()
        (d / "SKILL.md").write_text("""---
name: bad-skill
---
# No permissions field
""", encoding="utf-8")
        result = validate_skill(d)
        assert not result.ok
        assert any("permissions" in e for e in result.errors)

    def test_invalid_permission_value_fails(self, tmp_path):
        """Invalid permission values should be caught."""
        from runtime.sdk.validate import validate_skill
        d = tmp_path / "bad-perm"
        d.mkdir()
        (d / "SKILL.md").write_text("""---
name: bad-perm
version: 1.0.0
display_name: Bad Perm
description: Test
permissions:
  network: superuser
  filesystem: read
  shell: none
  timeout: 30
---
""", encoding="utf-8")
        result = validate_skill(d)
        assert not result.ok


# ── Test Skill Packaging ────────────────────────────────────────────


class TestSkillPackage:
    """4.X.2: Skill packaging into distributable format."""

    def test_package_creates_tar_gz(self, temp_skill_dir, tmp_path):
        """Package should create .tar.gz archive."""
        from runtime.sdk.package import package_skill
        output = tmp_path / "output"
        output.mkdir()
        archive = package_skill(temp_skill_dir, output_dir=output)
        assert archive.exists()
        assert archive.suffix == ".gz" or archive.suffixes == [".tar", ".gz"]
        assert archive.stat().st_size > 0

    def test_package_includes_manifest(self, temp_skill_dir, tmp_path):
        """Package should include a manifest.json with metadata."""
        from runtime.sdk.package import package_skill
        output = tmp_path / "output2"
        output.mkdir()
        package_skill(temp_skill_dir, output_dir=output, include_manifest=True)
        manifest = output / "manifest.json"
        assert manifest.exists()
        meta = json.loads(manifest.read_text(encoding="utf-8"))
        assert meta["name"] == "test-skill"
        assert meta["version"] == "1.0.0"


# ── Test Skill Publishing ───────────────────────────────────────────


class TestSkillPublish:
    """4.X.2: Skill publishing to local registry."""

    def test_publish_to_local_registry(self, temp_skill_dir, tmp_path):
        """Publish should register skill in local registry."""
        from runtime.sdk.publish import publish_skill
        from runtime.sdk.package import package_skill

        output = tmp_path / "output"
        output.mkdir()
        archive = package_skill(temp_skill_dir, output_dir=output)

        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()
        result = publish_skill(archive, registry_dir=registry_dir)
        assert result.ok
        # The published dir name matches the temp skill dir name
        assert any(d.is_dir() for d in registry_dir.iterdir())

    def test_publish_duplicate_detected(self, temp_skill_dir, tmp_path):
        """Publishing duplicate skill should warn or fail."""
        from runtime.sdk.publish import publish_skill
        from runtime.sdk.package import package_skill

        output = tmp_path / "output"
        output.mkdir()
        archive = package_skill(temp_skill_dir, output_dir=output)

        registry_dir = tmp_path / "registry"
        registry_dir.mkdir()
        publish_skill(archive, registry_dir=registry_dir)
        # Second publish of same version should fail
        result = publish_skill(archive, registry_dir=registry_dir)
        assert not result.ok
