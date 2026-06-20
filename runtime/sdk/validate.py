"""validate: check SKILL.md correctness before packaging."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


_REQUIRED_FIELDS = {"name", "version", "display_name", "description", "permissions"}
_REQUIRED_PERMISSIONS = {"network", "filesystem", "shell", "timeout"}
_VALID_NETWORK = {"none", "localhost", "restricted", "any"}
_VALID_FILESYSTEM = {"none", "read", "readwrite"}
_VALID_SHELL = {"none", "readonly", "full"}


def validate_skill(skill_dir: Path) -> ValidationResult:
    """Validate a skill directory.

    Checks:
    1. SKILL.md exists
    2. YAML frontmatter is valid
    3. Required fields present
    4. Permission values are valid
    """
    errors: list[str] = []
    warnings: list[str] = []

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        errors.append("Missing SKILL.md")
        return ValidationResult(ok=False, errors=errors)

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        errors.append("SKILL.md missing YAML frontmatter (must start with ---)")
        return ValidationResult(ok=False, errors=errors)

    # Parse YAML frontmatter
    parts = content.split("---")
    if len(parts) < 3:
        errors.append("SKILL.md has malformed YAML frontmatter")
        return ValidationResult(ok=False, errors=errors)

    try:
        import yaml
        meta = yaml.safe_load(parts[1])
    except ImportError:
        errors.append("PyYAML not installed (required for SKILL.md validation)")
        return ValidationResult(ok=False, errors=errors)
    except Exception as e:
        errors.append(f"YAML parse error: {e}")
        return ValidationResult(ok=False, errors=errors)

    if not isinstance(meta, dict):
        errors.append("YAML frontmatter must be a mapping")
        return ValidationResult(ok=False, errors=errors)

    # Check required fields
    for field in _REQUIRED_FIELDS:
        if field not in meta:
            errors.append(f"Missing required field: {field}")

    # Check permissions
    if "permissions" in meta:
        perms = meta["permissions"]
        if not isinstance(perms, dict):
            errors.append("permissions must be a mapping")
        else:
            for p in _REQUIRED_PERMISSIONS:
                if p not in perms:
                    errors.append(f"Missing required permission: {p}")
            if "network" in perms and perms["network"] not in _VALID_NETWORK:
                errors.append(
                    f"Invalid network permission: {perms['network']}. "
                    f"Must be one of: {', '.join(sorted(_VALID_NETWORK))}"
                )
            if "filesystem" in perms and perms["filesystem"] not in _VALID_FILESYSTEM:
                errors.append(
                    f"Invalid filesystem permission: {perms['filesystem']}. "
                    f"Must be one of: {', '.join(sorted(_VALID_FILESYSTEM))}"
                )
            if "shell" in perms and perms["shell"] not in _VALID_SHELL:
                errors.append(
                    f"Invalid shell permission: {perms['shell']}. "
                    f"Must be one of: {', '.join(sorted(_VALID_SHELL))}"
                )
    else:
        errors.append("Missing required field: permissions")

    return ValidationResult(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
