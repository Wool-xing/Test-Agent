"""Adapter: invoke an expert / skill defined in markdown.

Expert/Skill execution model:

- The 14 experts and 13 skills live as markdown. They are designed for Claude Code
  agents to load and execute. Outside of Claude Code, we treat each expert as a
  declarative description and execute its CANONICAL SCRIPT mapping (below).
- A handful of experts have a strong default script. The rest fall back to
  recording the expert step + producing an empty result placeholder which the
  report-generator then summarises (matching V1.0.0 manual workflow).
- Scripts with required CLI args(e.g. generate_report.py --data)get default
  inputs auto-injected via SCRIPT_DEFAULT_ARGS;referenced fixtures auto-materialized
  by _ensure_fixture (V1.11 修 V1.10 n7 selftest bug)。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from runtime.orchestrator.adapters.scripts import ScriptResult, list_available_scripts, run_script

# Canonical script mapping. Names without a script run as a no-op step (logged only).
# Mapping derived from existing 05-代码示例 filenames; missing scripts degrade gracefully.
EXPERT_SCRIPT_MAP: dict[str, str | None] = {
    "test-lead": None,
    "requirements-analyst": None,
    "testcase-designer": "excel_generator.py",
    "env-manager": None,
    "data-preparer": "data_factory.py",
    "automation-engineer": None,
    "test-executor": None,
    "bug-manager": None,
    "report-generator": "generate_report.py",
    "mobile-tester": None,
    "desktop-tester": "desktop_driver.py",
    "visual-tester": None,
    "system-tester": None,
    "ai-tester": "ai_validator.py",
}

SKILL_SCRIPT_MAP: dict[str, str | None] = {
    "smoke-test": None,
    "regression-test": None,
    "testcase-design": "excel_generator.py",
    "python-script-gen": None,
    "jmeter-script-gen": None,
    "data-preparation": "data_factory.py",
    "zentao-bug-submission": None,
    "test-coordinator": None,
    "mobile-test": None,
    "desktop-test": "desktop_driver.py",
    "visual-test": None,
    "system-test": None,
    "ai-test": "ai_validator.py",
}

# Scripts that require CLI args; injected when DAG node provides no inputs.
# Explicit DAG inputs always win; defaults only fill the gap.
SCRIPT_DEFAULT_ARGS: dict[str, dict[str, str]] = {
    "generate_report.py": {"data": "workspace/执行日志/_selftest_summary.json"},
}

# Fixture content materialized on demand when a SCRIPT_DEFAULT_ARGS value points to
# a missing file. Keys are workspace-relative paths.
SCRIPT_FIXTURES: dict[str, dict] = {
    "workspace/执行日志/_selftest_summary.json": {
        "project_name": "Test-Agent selftest fixture",
        "version": "0.0.0-selftest",
        "environment": "ci",
        "verdict": "通过",
        "results": {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0},
        "bugs": {"p0": 0, "p0_fix_rate": 0.0, "p1": 0, "p1_fix_rate": 0.0, "p2": 0, "p2_fix_rate": 0.0, "p3": 0, "p3_fix_rate": 0.0},
        "coverage": 0.0,
        "risks": [{"level": "低", "desc": "selftest fixture - no real data", "owner": "ci"}],
    },
}


def _ensure_fixture(path_str: str) -> None:
    """Materialize a default fixture file if absent. Keys match SCRIPT_FIXTURES."""
    p = Path(path_str)
    if p.exists():
        return
    fixture = SCRIPT_FIXTURES.get(path_str)
    if fixture is None:
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")


@dataclass(slots=True)
class StepOutcome:
    name: str
    kind: str  # expert|skill|script
    executed_script: str | None
    returncode: int | None
    stdout: str
    stderr: str
    duration_ms: int

    @property
    def ok(self) -> bool:
        return self.returncode in (None, 0)


def _resolve_script(name: str, kind: str) -> str | None:
    if kind == "expert":
        return EXPERT_SCRIPT_MAP.get(name)
    if kind == "skill":
        return SKILL_SCRIPT_MAP.get(name)
    if kind == "script":
        return name
    return None


def execute_node(name: str, kind: str, *, inputs: dict | None = None, timeout: int = 1800) -> StepOutcome:
    inputs = inputs or {}
    script = _resolve_script(name, kind)
    if script is None:
        return StepOutcome(
            name=name,
            kind=kind,
            executed_script=None,
            returncode=None,
            stdout=f"[no-op] {kind} '{name}' has no canonical script; documented step recorded.",
            stderr="",
            duration_ms=0,
        )
    available = set(list_available_scripts())
    if script not in available:
        return StepOutcome(
            name=name,
            kind=kind,
            executed_script=script,
            returncode=127,
            stdout="",
            stderr=f"script '{script}' not found under 05-代码示例/",
            duration_ms=0,
        )
    defaults = SCRIPT_DEFAULT_ARGS.get(script, {})
    merged = {**defaults, **inputs}  # explicit inputs win
    for k, v in defaults.items():
        if k not in inputs:  # only materialize fixture for auto-injected defaults
            _ensure_fixture(str(v))
    args = [f"--{k}={v}" for k, v in merged.items()]
    res: ScriptResult = run_script(script, args=args, timeout=timeout)
    return StepOutcome(
        name=name,
        kind=kind,
        executed_script=script,
        returncode=res.returncode,
        stdout=res.stdout,
        stderr=res.stderr,
        duration_ms=res.duration_ms,
    )
