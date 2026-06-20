"""publish: publish a packaged Skill to a local or remote registry."""

from __future__ import annotations

import re
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

_VALID_SKILL_NAME = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$')


@dataclass
class PublishResult:
    ok: bool
    message: str = ""
    errors: list[str] = field(default_factory=list)


def _validate_tar_members(members: list[tarfile.TarInfo]) -> None:
    """CRITICAL: Block path traversal (zip slip) in tar entries.

    Validates that no entry contains absolute paths or '..' components.
    Raises ValueError on unsafe entries.
    """
    for member in members:
        member_path = Path(member.name)
        if member_path.is_absolute() or ".." in member_path.parts:
            raise ValueError(
                f"Unsafe tar entry '{member.name}': "
                f"absolute paths and '..' components are forbidden."
            )


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

    with tarfile.open(archive_path, "r:gz") as tar:
        members = tar.getmembers()
        _validate_tar_members(members)

        # Detect skill name from first non-dot component in archive
        skill_name = None
        for m in members:
            parts = Path(m.name).parts
            if parts and parts[0] not in (".", ".."):
                skill_name = parts[0]
                break

        if not skill_name:
            return PublishResult(ok=False, errors=["Cannot determine skill name from archive"])

        # Validate skill_name against kebab-case pattern
        if not _VALID_SKILL_NAME.match(skill_name):
            return PublishResult(
                ok=False,
                errors=[f"Invalid skill name in archive: '{skill_name}'. "
                        f"Must be kebab-case (e.g. 'my-http-check')."],
            )

        target_dir = registry_dir / skill_name
        if target_dir.exists():
            return PublishResult(
                ok=False,
                errors=[f"Skill '{skill_name}' already exists in registry"],
            )

        # Safe extraction: filter="data" on Python >=3.12, manual guard on older
        import sys
        if sys.version_info >= (3, 12):
            tar.extractall(registry_dir, filter="data")
        else:
            # Python 3.10/3.11 fallback: members already validated by _validate_tar_members
            tar.extractall(registry_dir)

    return PublishResult(ok=True, message=f"Published {skill_name} to {registry_dir}")


def _default_registry() -> Path:
    """Return default local registry path."""
    return Path.home() / ".tagent" / "skills"
