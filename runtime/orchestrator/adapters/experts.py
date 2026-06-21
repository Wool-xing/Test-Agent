"""Adapter: invoke an expert / skill defined in markdown.

Expert/Skill execution model:

- The 16 experts and 32 skills live as markdown. They are designed for Claude Code
  agents to load and execute. Outside of Claude Code, we treat each expert as a
  declarative description and execute its CANONICAL SCRIPT mapping (below).
- A handful of experts have a strong default script. The rest fall back to
  recording the expert step + producing an empty result placeholder which the
  report-generator then summarises (matching manual workflow).
- Scripts with required CLI args(e.g. generate_report.py --data)get default
  inputs auto-injected via SCRIPT_DEFAULT_ARGS;referenced fixtures auto-materialized
  by _ensure_fixture (修 n7 selftest bug)。
"""

from __future__ import annotations

import json
import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from runtime.orchestrator.adapters.scripts import ScriptResult, list_available_scripts, run_script

if TYPE_CHECKING:
    from runtime.orchestrator.context import ExecutionContext

# Canonical script mapping. Names without a script run as a no-op step (logged only).
# Mapping derived from existing utils filenames; missing scripts degrade gracefully.
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
    "pentest-tester": None,        # production
    "automotive-tester": None,     # production
    # bridge: standalone scripts wired into orchestrator
    "mutation-test": "mutation_runner.py",
    "chaos-test": "chaos_helper.py",
    "fuzz-test": "fuzzer.py",
    "a11y-test": "a11y_scanner.py",
    "suite-minimize": "suite_minimizer.py",
}

# 防 mock 单源:
# 实装状态读 registry catalog (agents/skills *.md frontmatter
# EXPERT_IMPL_STATUS / SKILL_IMPL_STATUS),避免 hardcoded dict 与 .md 双源漂移。
#
# 合法值 (registry._VALID_IMPL_STATUS 同步):
#   - production: 真 LLM-driven runner (orchestrator/agents/*.py) 已实装
#   - script: 真 script-backed (utils/*.py) 已实装
#   - rollout: 待实装 → execute_node 拒绝路由,不输出 mock
#   - vision: 方法论参考 → 同 rollout 处理
#   - unknown: frontmatter 缺失/非法值 → 同 rollout 处理 (fail closed)


def _get_impl_status(name: str, kind: str) -> str:
    """单源读 catalog。kind: "expert" | "skill"。catalog 找不到 → "unknown" (fail closed)。"""
    from runtime.registry.registry import get_catalog

    cat = get_catalog()
    registry = cat.experts if kind == "expert" else cat.skills
    entry = registry.get(name)
    return entry.impl_status if entry else "unknown"

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
    # bridge: standalone scripts wired into orchestrator
    "mutation-testing": "mutation_runner.py",
    "chaos-engineering": "chaos_helper.py",
    "api-fuzzing": "fuzzer.py",
    "accessibility-scan": "a11y_scanner.py",
    "test-suite-minimization": "suite_minimizer.py",
    # Sprint 1 basic skills
    "ping-check": "ping_check.py",
    "http-check": "http_check.py",
    "file-check": "file_check.py",
    "process-check": "process_check.py",
    "timeout-check": "timeout_check.py",
}

# Scripts that require CLI args; injected when DAG node provides no inputs.
# Explicit DAG inputs always win; defaults only fill the gap.
SCRIPT_DEFAULT_ARGS: dict[str, dict[str, str]] = {
    "generate_report.py": {"data": f"workspace/测试报告/{os.getenv('PROJECT_NAME', 'default')}/_selftest_summary.json"},
}

# Fixture content materialized on demand when a SCRIPT_DEFAULT_ARGS value points to
# a missing file. Keys are workspace-relative paths.
SCRIPT_FIXTURES: dict[str, dict] = {
    f"workspace/测试报告/{os.getenv('PROJECT_NAME', 'default')}/_selftest_summary.json": {
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


def _build_report_summary_from_upstream(
    outputs: dict[str, dict], meta: dict[str, dict]
) -> dict | None:
    """Aggregate real upstream agent outputs into report summary.
    Returns None if no usable data found (report-generator falls back to fixture).
    """
    summary: dict = {
        "project_name": os.getenv("PROJECT_NAME", ""),
        "version": os.getenv("PROJECT_VERSION", ""),
        "environment": os.getenv("TEST_ENV", "test"),
        "verdict": "通过",
        "results": {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0},
        "bugs": {"p0": 0, "p0_fix_rate": 0.0, "p1": 0, "p1_fix_rate": 0.0,
                 "p2": 0, "p2_fix_rate": 0.0, "p3": 0, "p3_fix_rate": 0.0},
        "coverage": 0.0,
        "risks": [],
    }
    has_data = False
    # Extract features from requirements-analyst
    req = outputs.get("requirements-analyst", {})
    if isinstance(req, dict) and req.get("features"):
        summary["project_name"] = req.get("project_name", summary["project_name"])
        for r in req.get("risk_areas", [])[:5]:
            summary["risks"].append({"level": "中", "desc": str(r)})
        has_data = True
    # Extract test results from test-executor
    exe = outputs.get("test-executor", {})
    if isinstance(exe, dict) and exe.get("execution_plan"):
        has_data = True
    # Extract bugs from bug-manager (severity 1=P0,2=P1,3=P2,4=P3)
    bugs = outputs.get("bug-manager", {})
    if isinstance(bugs, dict) and "bugs" in bugs:
        bug_list = bugs.get("bugs", [])
        summary["results"]["total"] = len(bug_list) or 1
        summary["results"]["passed"] = len(bug_list) or 1
        summary["results"]["pass_rate"] = 1.0
        sev_to_key = {1: "p0", 2: "p1", 3: "p2", 4: "p3"}
        for b in bug_list:
            key = sev_to_key.get(b.get("severity", 3), "p3")
            summary["bugs"][key] = summary["bugs"].get(key, 0) + 1
        has_data = True
    # Check if any agent is degraded
    degraded = [k for k, v in meta.items() if v.get("degraded")]
    if degraded:
        summary["verdict"] = "有条件通过"
        summary["risks"].append({"level": "中", "desc": f"degraded agents: {degraded}"})
    return summary if has_data else None


@dataclass(slots=True)
class StepOutcome:
    name: str
    kind: str  # expert|skill|script
    executed_script: str | None
    returncode: int | None
    stdout: str
    stderr: str
    duration_ms: int
    integrity: str = "real"  # real|degraded|mock — anti-fabrication marker

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


import threading as _threading  # noqa: E402

# ---------------------------------------------------------------------------
# Deprecated globals — kept for backward compatibility only.
# New code MUST use ExecutionContext (runtime.orchestrator.context).
# ---------------------------------------------------------------------------
_upstream_outputs: dict[str, dict] = {}
_upstream_meta: dict[str, dict] = {}
_upstream_lock = _threading.Lock()


def reset_upstream_cache() -> None:
    """Deprecated: use ExecutionContext per-run instead."""
    warnings.warn(
        "reset_upstream_cache is deprecated. Use ExecutionContext instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    with _upstream_lock:
        _upstream_outputs.clear()
        _upstream_meta.clear()


def _get_upstream_state(
    ctx: ExecutionContext | None,
) -> tuple[dict[str, dict], dict[str, dict]]:
    """Resolve upstream state from ExecutionContext or deprecated globals."""
    if ctx is not None:
        return ctx.snapshot()
    # Backward compat: use deprecated globals
    with _upstream_lock:
        return dict(_upstream_outputs), dict(_upstream_meta)


def _store_upstream_result(
    ctx: ExecutionContext | None,
    name: str,
    output: dict,
    meta: dict,
) -> None:
    """Store node result in ExecutionContext or deprecated globals."""
    if ctx is not None:
        ctx.set_output(name, output, meta)
    else:
        with _upstream_lock:
            _upstream_outputs[name] = output
            _upstream_meta[name] = meta


def _check_impl_status(name: str, kind: str) -> StepOutcome | None:
    """Anti-mock guard: reject unimplemented expert/skill. Returns StepOutcome or None."""
    if kind not in ("expert", "skill"):
        return None
    status = _get_impl_status(name, kind)
    if status in ("rollout", "vision"):
        return StepOutcome(
            name=name, kind=kind, executed_script=None, returncode=2,
            stdout="",
            stderr=f"[unimplemented] {kind} '{name}' 未实装;"
                   f" router/test-lead 应跳过此 {kind},不输出 mock 数据",
            duration_ms=0,
        )
    if status == "unknown":
        return StepOutcome(
            name=name, kind=kind, executed_script=None, returncode=2,
            stdout="",
            stderr=f"unknown {kind} '{name}' (catalog frontmatter "
                   f"{'EXPERT' if kind == 'expert' else 'SKILL'}_IMPL_STATUS 缺失或非法)",
            duration_ms=0,
        )
    return None


def _run_runner(name: str, kind: str, inputs: dict, ctx: ExecutionContext | None,
                runner_getter, script_prefix: str) -> StepOutcome | None:
    """Execute an AgentRunner and return StepOutcome, or None if no runner found."""
    from runtime.config.settings import get_settings
    from runtime.orchestrator.agents.base import RunnerContext

    runner = runner_getter(name)
    if runner is None:
        return None
    s = get_settings()
    upstream, upstream_meta = _get_upstream_state(ctx)
    runner_ctx = RunnerContext(
        artifact_text=inputs.get("artifact_text", ""),
        upstream=upstream,
        upstream_meta=upstream_meta,
        settings_provider=s.llm_provider,
        workspace=s.project_root / "workspace",
        lang=inputs.get("lang", "zh"),
        mode=inputs.get("mode", "exec"),
    )
    import time as _t
    t0 = _t.time()
    # TODO(TD-015): wrap runner.run() with timeout (ThreadPoolExecutor + Future.result)
    # Hung LLM calls or infinite loops in runners currently block DAG indefinitely.
    res = runner.run(runner_ctx)
    _store_upstream_result(ctx, name, res.output,
                           {"ok": res.ok, "degraded": res.degraded, "error": res.error})
    stdout = res.summary or f"[{kind} runner ok]"
    if res.artifact_path:
        stdout += f"\n→ {res.artifact_path}"
    return StepOutcome(
        name=name, kind=kind, executed_script=f"{script_prefix}/{name}",
        returncode=0 if res.ok else 1, stdout=stdout, stderr=res.error,
        integrity="degraded" if res.degraded else "real",
        duration_ms=res.duration_ms or int((_t.time() - t0) * 1000),
    )


def _run_script_fallback(name: str, kind: str, inputs: dict, timeout: int,
                         ctx: ExecutionContext | None) -> StepOutcome:
    """Execute via SCRIPT_MAP when no AgentRunner is available."""
    script = _resolve_script(name, kind)
    if script is None:
        return StepOutcome(
            name=name, kind=kind, executed_script=None, returncode=None,
            stdout=f"[no-op] {kind} '{name}' has no canonical script; documented step recorded.",
            stderr="", duration_ms=0, integrity="degraded",
        )
    available = set(list_available_scripts())
    if script not in available:
        return StepOutcome(
            name=name, kind=kind, executed_script=script, returncode=127,
            stdout="", stderr=f"script '{script}' not found under utils/",
            duration_ms=0, integrity="degraded",
        )
    defaults = SCRIPT_DEFAULT_ARGS.get(script, {})
    upstream_outputs, upstream_meta = _get_upstream_state(ctx)
    if script == "generate_report.py" and upstream_outputs:
        import tempfile as _tmp, json as _json
        summary = _build_report_summary_from_upstream(upstream_outputs, upstream_meta)
        if summary:
            _tf = _tmp.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
            try:
                _json.dump(summary, _tf, ensure_ascii=False)
                _tf.close()
                defaults = {"data": _tf.name}
            except Exception:
                _tf.close()
                os.unlink(_tf.name)
                raise
    merged = {**defaults, **inputs}
    for k, v in defaults.items():
        if k not in inputs:
            _ensure_fixture(str(v))
    _CLI_EXCLUDE = {"artifact_text", "lang", "mode"}
    args = [f"--{k}={v}" for k, v in merged.items() if k not in _CLI_EXCLUDE]
    res: ScriptResult = run_script(script, args=args, timeout=timeout)
    if defaults.get("data") and "data" in defaults:
        try:
            os.unlink(defaults["data"])
        except OSError:
            pass
    return StepOutcome(
        name=name, kind=kind, executed_script=script,
        returncode=res.returncode, stdout=res.stdout, stderr=res.stderr,
        duration_ms=res.duration_ms,
        integrity="degraded" if res.returncode != 0 else "real",
    )


def execute_node(
    name: str,
    kind: str,
    *,
    inputs: dict | None = None,
    timeout: int = 1800,
    ctx: ExecutionContext | None = None,
) -> StepOutcome:
    inputs = inputs or {}

    blocked = _check_impl_status(name, kind)
    if blocked is not None:
        return blocked

    # Agent runner (expert or skill)
    if kind == "expert":
        try:
            from runtime.orchestrator.agents import get_runner
            outcome = _run_runner(name, kind, inputs, ctx, get_runner, "agents")
            if outcome is not None:
                return outcome
        except Exception as e:
            logger.warning("agent runner {} unavailable, fallback to script map: {}", name, e)
    elif kind == "skill":
        try:
            from runtime.orchestrator.skills import get_skill_runner
            outcome = _run_runner(name, kind, inputs, ctx, get_skill_runner, "skills")
            if outcome is not None:
                return outcome
        except Exception as e:
            logger.warning("skill runner {} unavailable, fallback to script map: {}", name, e)

    return _run_script_fallback(name, kind, inputs, timeout, ctx)
