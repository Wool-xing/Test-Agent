"""ManifestV2 — Single source of truth for agent/skill definitions.

Pydantic v2 schema with semver validation, backend consistency checks,
and gate reference validation.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Enums ────────────────────────────────────────────────────────────────────


class Backend(str, Enum):
    LLM = "llm"
    SCRIPT = "script"
    NOOP = "noop"


class Kind(str, Enum):
    AGENT = "agent"
    SKILL = "skill"


# ── Semver regex ─────────────────────────────────────────────────────────────

_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?"
    r"(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$"
)


# ── Model ────────────────────────────────────────────────────────────────────


class ManifestV2(BaseModel):
    """Single source of truth for agent/skill definitions."""

    name: str = Field(description="Unique ID, e.g. 'test-lead', 'smoke-test'")
    version: str = Field(default="1.0.0", description="Semver")
    kind: Kind
    description: str = Field(description="One-line role description")
    description_zh: str = Field(default="", description="Chinese description")
    backend: Backend = Backend.LLM
    tools: list[str] = Field(
        default_factory=list,
        description="Allowed tools: Read, Write, Bash, Grep, Glob, Edit",
    )
    paired_skills: list[str] = Field(
        default_factory=list,
        description="Skill names this agent pairs with",
    )
    script_path: Optional[str] = Field(
        default=None,
        description="For script-backed: path relative to utils/",
    )
    requires_layer: list[str] = Field(
        default_factory=list,
        description="Required layers: base, security, etc.",
    )
    system_prompt: str = Field(
        default="",
        description="System prompt for LLM-driven agents",
    )
    output_schema: dict = Field(
        default_factory=dict,
        description="JSON Schema for structured output",
    )
    gates: list[str] = Field(
        default_factory=list,
        description="Gate names referenced from specs/gates/",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Search/discovery tags",
    )
    deprecated: bool = Field(default=False)

    model_config = {"extra": "forbid"}

    # ── Validators ───────────────────────────────────────────────────────

    @field_validator("version")
    @classmethod
    def _version_is_semver(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError(f"version must be semver (MAJOR.MINOR.PATCH), got: {v!r}")
        return v

    @field_validator("name")
    @classmethod
    def _name_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must be non-empty")
        return v.strip()

    @field_validator("description")
    @classmethod
    def _description_nonempty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("description must be non-empty")
        return v.strip()

    @model_validator(mode="after")
    def _backend_script_needs_path(self):
        if self.backend == Backend.SCRIPT and not self.script_path:
            raise ValueError("script_path is required when backend is 'script'")
        return self


# ── Validation function ──────────────────────────────────────────────────────


def validate_manifest(m: ManifestV2) -> list[str]:
    """Validate a ManifestV2 instance beyond what Pydantic catches.

    Returns a list of validation error messages. An empty list means valid.
    """
    errors: list[str] = []

    # Check gate references point to real files
    gates_dir = Path(__file__).resolve().parent / "gates"
    for gate_name in m.gates:
        gate_file = gates_dir / f"{gate_name}.yaml"
        if not gate_file.is_file():
            errors.append(
                f"gate '{gate_name}' not found: expected file at {gate_file}"
            )

    return errors
