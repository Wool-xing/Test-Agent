"""publish: publish a packaged Skill to a local or remote registry."""

from __future__ import annotations

import shutil
import tarfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PublishResult:
    ok: bool
    message: str = ""
    errors: list[str] = field(default_factory=list)


def publish_skill(
    archive_path: Path,
    *,
    registry_dir: Path | None = None,
) -> PublishResult:
    """Publish a packaged skill (.tar.gz) to a local registry.

    Args:
        archive_path: Path to the .tar.gz skill archive.
        registry_dir: Local registry directory. Defaults to ~/.tagent/skills/.

    Returns:
        PublishResult with ok=True on success.
    """
    if not archive_path.exists():
        return PublishResult(ok=False, errors=[f"Archive not found: {archive_path}"])

    registry_dir = (registry_dir or _default_registry()).resolve()
    registry_dir.mkdir(parents=True, exist_ok=True)

    # Extract archive to temp, then detect skill name
    with tarfile.open(archive_path, "r:gz") as tar:
        members = tar.getmembers()
        # Find the skill directory name (first component of archive paths)
        skill_name = None
        for m in members:
            parts = Path(m.name).parts
            if parts:
                candidate = parts[0]
                if candidate not in (".", ".."):
                    skill_name = candidate
                    break

        if not skill_name:
            return PublishResult(ok=False, errors=["Cannot determine skill name from archive"])

        target_dir = registry_dir / skill_name
        if target_dir.exists():
            return PublishResult(
                ok=False,
                errors=[f"Skill '{skill_name}' already exists in registry"],
            )

        # Extract to registry
        tar.extractall(registry_dir, filter="data")

    return PublishResult(ok=True, message=f"Published {skill_name} to {registry_dir}")


def _default_registry() -> Path:
    """Return default local registry path."""
    return Path.home() / ".tagent" / "skills"
