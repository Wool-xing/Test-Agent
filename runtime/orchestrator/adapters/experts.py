"""Adapter: invoke an expert / skill defined in markdown.

Expert/Skill execution model:

- The 14 experts and 13 skills live as markdown. They are designed for Claude Code
  agents to load and execute. Outside of Claude Code, we treat each expert as a
  declarative description and execute its CANONICAL SCRIPT mapping (below).
- A handful of experts have a strong default script. The rest fall back to
  recording the expert step + producing an empty result placeholder which the
  report-generator then summarises (matching V1.0.0 manual workflow).
"""

from __future__ import annotations

from dataclasses import dataclass

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
    args = [f"--{k}={v}" for k, v in inputs.items()]
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
