"""Install a skill from a local directory into a workspace."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class InstallResult:
    ok: bool
    error: str = ""
    target_path: str = ""


def install_skill(source: Path, workspace: Path) -> InstallResult:
    """Install a skill from a local directory into a workspace skills directory.

    Args:
        source: Path to the skill source directory (must contain SKILL.md).
        workspace: Path to the workspace root (skills/ subdirectory is the target).

    Returns:
        InstallResult with ok=True on success, or ok=False with error message.
    """
    skill_md = source / "SKILL.md"
    if not skill_md.is_file():
        return InstallResult(ok=False, error="Missing SKILL.md in source directory")

    # Parse name from SKILL.md frontmatter for validation
    name = _extract_skill_name(skill_md)
    if not name:
        return InstallResult(ok=False, error="SKILL.md missing 'name' field in frontmatter")

    # Validate kebab-case
    if not _is_kebab_case(name):
        return InstallResult(
            ok=False,
            error=f"Skill name '{name}' is not valid kebab-case. Use lowercase letters, digits, and hyphens only.",
        )

    target = workspace / "skills" / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return InstallResult(ok=True, target_path=str(target))


def _extract_skill_name(skill_md: Path) -> str | None:
    """Extract the name field from SKILL.md YAML frontmatter."""
    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None
    parts = content.split("---")
    if len(parts) < 3:
        return None
    try:
        import yaml
        meta = yaml.safe_load(parts[1])
    except Exception:
        return None
    if not isinstance(meta, dict):
        return None
    return meta.get("name", "").strip() or None


def _is_kebab_case(name: str) -> bool:
    """Check if a name is valid kebab-case (lowercase letters, digits, hyphens)."""
    return all(c.islower() or c.isdigit() or c == '-' for c in name) and len(name) > 0
