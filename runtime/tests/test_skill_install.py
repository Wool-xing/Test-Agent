"""TDD: Skill install — local path installation (Sprint 3)."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_skill_dir(tmp_path):
    """Create a minimal installable skill directory."""
    skill = tmp_path / "my-test-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("""---
name: my-test-skill
version: 1.0.0
display_name: My Test Skill
description: A test skill for install verification
permissions:
  network: none
  filesystem: read
  shell: none
  timeout: 30
---
# My Test Skill

## Quick Start
```bash
tagent "run my-test-skill check"
```
""", encoding="utf-8")
    (skill / "executor.py").write_text('''"""Minimal executor for my-test-skill."""

def execute(params, ctx):
    return {"status": "pass", "summary": "Test skill executed", "details": {}, "checks": [], "error": None}
''', encoding="utf-8")
    return skill


@pytest.fixture
def workspace_dir(tmp_path):
    """Simulate a Test-Agent workspace."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "skills").mkdir()
    return ws


class TestSkillInstall:
    """Install a skill from a local directory."""

    def test_install_copies_skill_to_workspace(self, sample_skill_dir, workspace_dir):
        """Installing a skill copies it to workspace/skills/<name>."""
        from runtime.sdk.install import install_skill
        result = install_skill(sample_skill_dir, workspace_dir)
        assert result.ok is True
        target = workspace_dir / "skills" / "my-test-skill"
        assert target.is_dir()
        assert (target / "SKILL.md").is_file()
        assert (target / "executor.py").is_file()

    def test_install_missing_skill_md_fails(self, tmp_path, workspace_dir):
        """Installing a directory without SKILL.md should fail."""
        bad = tmp_path / "no-skill-md"
        bad.mkdir()
        from runtime.sdk.install import install_skill
        result = install_skill(bad, workspace_dir)
        assert result.ok is False
        assert "SKILL.md" in result.error

    def test_install_overwrite_existing(self, sample_skill_dir, workspace_dir):
        """Re-installing should overwrite existing skill."""
        from runtime.sdk.install import install_skill
        # First install
        install_skill(sample_skill_dir, workspace_dir)
        # Second install (overwrite)
        result = install_skill(sample_skill_dir, workspace_dir)
        assert result.ok is True

    def test_install_validates_name(self, tmp_path, workspace_dir):
        """Skill name must be kebab-case."""
        bad = tmp_path / "Bad Name"
        bad.mkdir()
        (bad / "SKILL.md").write_text("""---
name: Bad Name
version: 1.0.0
display_name: Bad
description: bad name
permissions:
  network: none
  filesystem: none
  shell: none
  timeout: 30
---
""", encoding="utf-8")
        from runtime.sdk.install import install_skill
        result = install_skill(bad, workspace_dir)
        assert result.ok is False
        assert "kebab-case" in result.error.lower()


class TestSkillTest:
    """Run a skill's self-tests."""

    def test_skill_test_runs_pytest(self, sample_skill_dir, workspace_dir):
        """tagent skill test should run the skill's test file."""
        from runtime.sdk.install import install_skill
        install_skill(sample_skill_dir, workspace_dir)
        # Add a test file
        test_file = workspace_dir / "skills" / "my-test-skill" / "test_my_test_skill.py"
        test_file.write_text("""
def test_pass():
    assert True

def test_fail():
    assert False, "expected failure for test harness"
""", encoding="utf-8")
        from runtime.sdk.test_runner import run_skill_tests
        result = run_skill_tests("my-test-skill", workspace_dir / "skills")
        assert result.total >= 2
        assert result.failed >= 1

    def test_skill_test_missing_skill(self, workspace_dir):
        """Testing a non-existent skill should report error."""
        from runtime.sdk.test_runner import run_skill_tests
        result = run_skill_tests("nonexistent", workspace_dir / "skills")
        assert result.ok is False
