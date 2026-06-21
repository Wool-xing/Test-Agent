"""Skill discovery — scan local directories for installed skills.

Reads SKILL.md files from one or more skill directories and returns
a list of metadata dicts suitable for the catalog and registry.
"""

from __future__ import annotations

from pathlib import Path


def discover_skills(root: Path) -> list[dict]:
    """Scan a skill registry directory and return metadata for every skill.

    Each subdirectory containing a valid SKILL.md is treated as one skill.
    The YAML frontmatter is parsed for name, version, description, permissions,
    and other standard fields.

    Args:
        root: Path to a directory containing skill subdirectories.

    Returns:
        List of skill metadata dicts.  Empty list if the directory does not
        exist or contains no skills.
    """
    skills: list[dict] = []
    if not root.is_dir():
        return skills

    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            continue

        meta = _parse_frontmatter(skill_md)
        if meta:
            skills.append(meta)

    return skills


def _parse_frontmatter(skill_md: Path) -> dict | None:
    """Parse YAML frontmatter from a SKILL.md file."""
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

    return meta
