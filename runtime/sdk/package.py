"""package: bundle a Skill into a distributable .tar.gz archive."""

from __future__ import annotations

import json
import logging
import tarfile
from pathlib import Path

logger = logging.getLogger(__name__)


def package_skill(
    skill_dir: Path,
    *,
    output_dir: Path | None = None,
    include_manifest: bool = False,
) -> Path:
    """Package a skill directory into .tar.gz archive.

    Args:
        skill_dir: Path to the skill directory containing SKILL.md.
        output_dir: Output directory for the archive. Defaults to skill_dir parent.
        include_manifest: If True, also write manifest.json to output_dir.

    Returns:
        Path to the created .tar.gz archive.
    """
    skill_dir = skill_dir.resolve()
    name = skill_dir.name
    output_dir = (output_dir or skill_dir.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    archive_path = output_dir / f"{name}.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        for f in skill_dir.rglob("*"):
            if f.is_file():
                arcname = f.relative_to(skill_dir.parent)
                tar.add(f, arcname=arcname)

    if include_manifest:
        _write_manifest(skill_dir, output_dir)

    return archive_path


def _write_manifest(skill_dir: Path, output_dir: Path) -> None:
    """Generate manifest.json from SKILL.md frontmatter."""
    skill_md = skill_dir / "SKILL.md"
    try:
        content = skill_md.read_text(encoding="utf-8")
        parts = content.split("---")
        if len(parts) < 3:
            raise ValueError("Malformed SKILL.md: missing YAML frontmatter")
        import yaml
        meta = yaml.safe_load(parts[1])
        if not isinstance(meta, dict):
            raise ValueError("SKILL.md frontmatter is not a valid YAML mapping")
        manifest = output_dir / "manifest.json"
        manifest.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to generate manifest for %s: %s", skill_dir, e)
