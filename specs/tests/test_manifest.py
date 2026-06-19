"""Tests for ManifestV2 schema and validate_manifest."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from specs.manifest import Backend, Kind, ManifestV2, validate_manifest


# ── Helpers ──────────────────────────────────────────────────────────────────


def _valid_kwargs(**overrides):
    """Return kwargs for a valid ManifestV2, with optional overrides."""
    base = {
        "name": "test-lead",
        "kind": Kind.AGENT,
        "description": "Lead test coordinator",
    }
    base.update(overrides)
    return base


# ── Test: valid manifest creation ────────────────────────────────────────────


def test_valid_manifest_minimal():
    """Minimal required fields produce a valid manifest."""
    m = ManifestV2(name="smoke-test", kind=Kind.SKILL, description="Run smoke tests")
    assert m.name == "smoke-test"
    assert m.kind == Kind.SKILL
    assert m.version == "1.0.0"
    assert m.backend == Backend.LLM
    assert m.tools == []
    assert m.gates == []


def test_valid_manifest_full():
    """All fields populated produce a valid manifest."""
    m = ManifestV2(
        name="test-lead",
        version="2.0.0",
        kind=Kind.AGENT,
        description="Lead test coordinator",
        description_zh="test coordinator",
        backend=Backend.LLM,
        tools=["Read", "Write", "Bash"],
        paired_skills=["smoke-test"],
        requires_layer=["base", "security"],
        system_prompt="You are a test lead.",
        output_schema={"type": "object"},
        gates=[],
        tags=["core", "orchestrator"],
        deprecated=False,
    )
    assert m.version == "2.0.0"
    assert m.tools == ["Read", "Write", "Bash"]


def test_validate_manifest_returns_empty_for_valid():
    """validate_manifest returns empty list for a valid manifest with no gates."""
    m = ManifestV2(**_valid_kwargs())
    errors = validate_manifest(m)
    assert errors == []


# ── Test: missing required fields ────────────────────────────────────────────


def test_missing_name():
    """name is required."""
    with pytest.raises(ValidationError) as exc:
        ManifestV2(kind=Kind.AGENT, description="Desc")
    errors = exc.value.errors()
    assert any(e["loc"] == ("name",) for e in errors)


def test_missing_kind():
    """kind is required."""
    with pytest.raises(ValidationError) as exc:
        ManifestV2(name="test", description="Desc")
    errors = exc.value.errors()
    assert any(e["loc"] == ("kind",) for e in errors)


def test_missing_description():
    """description is required."""
    with pytest.raises(ValidationError) as exc:
        ManifestV2(name="test", kind=Kind.AGENT)
    errors = exc.value.errors()
    assert any(e["loc"] == ("description",) for e in errors)


def test_empty_name():
    """Empty name should be rejected."""
    with pytest.raises(ValidationError) as exc:
        ManifestV2(name="   ", kind=Kind.AGENT, description="Desc")
    errors = exc.value.errors()
    assert any(e["loc"] == ("name",) for e in errors)


def test_empty_description():
    """Empty description should be rejected."""
    with pytest.raises(ValidationError) as exc:
        ManifestV2(name="test", kind=Kind.AGENT, description="")
    errors = exc.value.errors()
    assert any(e["loc"] == ("description",) for e in errors)


# ── Test: version format validation (semver) ─────────────────────────────────


@pytest.mark.parametrize(
    "bad_version",
    [
        "1",
        "1.0",
        "v1.0.0",
        "1.0.0.0",
        "abc",
        "",
        "latest",
        "1.0.0-",
    ],
)
def test_invalid_version_format(bad_version: str):
    """Non-semver version strings are rejected."""
    with pytest.raises(ValidationError) as exc:
        ManifestV2(name="test", kind=Kind.AGENT, description="Desc", version=bad_version)
    errors = exc.value.errors()
    assert any(e["loc"] == ("version",) for e in errors)


@pytest.mark.parametrize(
    "good_version",
    [
        "0.0.0",
        "1.0.0",
        "10.20.30",
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0+build",
        "1.0.0-alpha+build",
    ],
)
def test_valid_version_format(good_version: str):
    """Valid semver strings are accepted."""
    m = ManifestV2(
        **_valid_kwargs(version=good_version)
    )
    assert m.version == good_version


# ── Test: gate reference validation ──────────────────────────────────────────


def test_gate_reference_valid():
    """smoke-gate exists in specs/gates/, so it validates."""
    m = ManifestV2(**_valid_kwargs(gates=["smoke-gate"]))
    errors = validate_manifest(m)
    assert errors == []


def test_gate_reference_missing():
    """A gate reference that doesn't exist produces an error."""
    m = ManifestV2(**_valid_kwargs(gates=["nonexistent-gate"]))
    errors = validate_manifest(m)
    assert len(errors) == 1
    assert "nonexistent-gate" in errors[0]
    assert "not found" in errors[0]


def test_gate_reference_multiple():
    """Multiple gate references — some valid, some not."""
    m = ManifestV2(**_valid_kwargs(gates=["smoke-gate", "missing-gate"]))
    errors = validate_manifest(m)
    assert len(errors) == 1
    assert "missing-gate" in errors[0]


# ── Test: backend validation (script must have script_path) ──────────────────


def test_llm_backend_without_script_path():
    """LLM backend doesn't need script_path."""
    m = ManifestV2(**_valid_kwargs(backend=Backend.LLM))
    assert m.script_path is None


def test_noop_backend_without_script_path():
    """NOOP backend doesn't need script_path."""
    m = ManifestV2(**_valid_kwargs(backend=Backend.NOOP))
    assert m.script_path is None


def test_script_backend_with_script_path():
    """SCRIPT backend with script_path is valid."""
    m = ManifestV2(
        **_valid_kwargs(backend=Backend.SCRIPT, script_path="smoke_runner.py")
    )
    assert m.backend == Backend.SCRIPT
    assert m.script_path == "smoke_runner.py"


def test_script_backend_missing_script_path():
    """SCRIPT backend without script_path should fail."""
    with pytest.raises(ValidationError) as exc:
        ManifestV2(**_valid_kwargs(backend=Backend.SCRIPT))
    errors = exc.value.errors()
    assert any("script_path" in str(e.get("msg", "")) for e in errors)


# ── Test: extra fields forbidden ─────────────────────────────────────────────


def test_extra_fields_forbidden():
    """model_config extra='forbid' rejects unknown fields."""
    with pytest.raises(ValidationError):
        ManifestV2(**_valid_kwargs(unknown_field="should not be here"))


# ── Test: Immutability (enum behavior) ───────────────────────────────────────


def test_backend_default_is_llm():
    """Default backend is LLM."""
    m = ManifestV2(**_valid_kwargs())
    assert m.backend == Backend.LLM


def test_kind_enum_values():
    """Kind enum has expected values."""
    assert Kind.AGENT.value == "agent"
    assert Kind.SKILL.value == "skill"


def test_backend_enum_values():
    """Backend enum has expected values."""
    assert Backend.LLM.value == "llm"
    assert Backend.SCRIPT.value == "script"
    assert Backend.NOOP.value == "noop"
