"""Adapter: invoke an expert / skill defined in markdown.

Expert/Skill execution model:

- The 16 experts and 32 skills live as markdown. They are designed for Claude Code
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

from loguru import logger

from runtime.orchestrator.adapters.scripts import ScriptResult, list_available_scripts, run_script

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
    "pentest-tester": None,        # V1.19 production (V1.x rollout 收尾)
    "automotive-tester": None,     # V1.20 production (V1.x rollout 收尾)
    # V1.34 bridge: standalone scripts wired into orchestrator
    "mutation-test": "mutation_runner.py",
    "chaos-test": "chaos_helper.py",
    "fuzz-test": "fuzzer.py",
    "a11y-test": "a11y_scanner.py",
    "suite-minimize": "suite_minimizer.py",
}

# V1.14 防 mock 单源 (ROADMAP V1.15 Day 0 承诺):
# 实装状态读 registry catalog (agents/skills *.md frontmatter
# EXPERT_IMPL_STATUS / SKILL_IMPL_STATUS),避免 hardcoded dict 与 .md 双源漂移。
#
# 合法值 (registry._VALID_IMPL_STATUS 同步):
#   - production: 真 LLM-driven runner (orchestrator/agents/*.py) 已实装
#   - script: 真 script-backed (utils/*.py) 已实装
#   - rollout: V1.x rollout 待实装 → execute_node 拒绝路由,不输出 mock
#   - vision: V2.x 方法论参考 → 同 rollout 处理
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
    # V1.34 bridge: standalone scripts wired into orchestrator
    "mutation-testing": "mutation_runner.py",
    "chaos-engineering": "chaos_helper.py",
    "api-fuzzing": "fuzzer.py",
    "accessibility-scan": "a11y_scanner.py",
    "test-suite-minimization": "suite_minimizer.py",
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


_upstream_outputs: dict[str, dict] = {}  # 流水线内每 expert 产物缓存,供下游 RunnerContext.upstream
_upstream_meta: dict[str, dict] = {}     # 流水线内每 expert 元信息 (ok/degraded/error),供下游 RunnerContext.upstream_meta
                                          # 防 mock 闭环: test-lead 看到任一 degraded → 决策降级


def reset_upstream_cache() -> None:
    """每次新 run 开始前由 flow 调,清空上游产物缓存."""
    _upstream_outputs.clear()
    _upstream_meta.clear()


def execute_node(name: str, kind: str, *, inputs: dict | None = None, timeout: int = 1800) -> StepOutcome:
    inputs = inputs or {}

    # V1.14 防 mock (ROADMAP V1.15 Day 0 承诺): 拒绝路由未实装 expert/skill,不输出 mock 数据
    # 单源 = agents/skills .md frontmatter (registry catalog)
    if kind in ("expert", "skill"):
        status = _get_impl_status(name, kind)
        if status in ("rollout", "vision"):
            return StepOutcome(
                name=name,
                kind=kind,
                executed_script=None,
                returncode=2,  # 明确非 0,标记 "未实装" 而非 no-op 兜底
                stdout="",
                stderr=(
                    f"[V1.x {status}] {kind} '{name}' 未实装 (ROADMAP.md);"
                    f" router/test-lead 应跳过此 {kind},不输出 mock 数据"
                ),
                duration_ms=0,
            )
        if status == "unknown":
            return StepOutcome(
                name=name,
                kind=kind,
                executed_script=None,
                returncode=2,
                stdout="",
                stderr=(
                    f"unknown {kind} '{name}' (catalog frontmatter "
                    f"{'EXPERT' if kind == 'expert' else 'SKILL'}_IMPL_STATUS 缺失或非法)"
                ),
                duration_ms=0,
            )

    # V1.14 真 agent runner 优先(主宪章 §40,5 核心 expert 落地)
    if kind == "expert":
        try:
            from runtime.config.settings import get_settings
            from runtime.orchestrator.agents import get_runner
            from runtime.orchestrator.agents.base import RunnerContext

            runner = get_runner(name)
            if runner is not None:
                s = get_settings()
                ctx = RunnerContext(
                    artifact_text=inputs.get("artifact_text", ""),
                    upstream=dict(_upstream_outputs),
                    upstream_meta=dict(_upstream_meta),
                    settings_provider=s.llm_provider,
                    workspace=s.project_root / "workspace",
                    lang=inputs.get("lang", "zh"),
                    mode=inputs.get("mode", "exec"),
                )
                import time as _t
                t0 = _t.time()
                res = runner.run(ctx)
                _upstream_outputs[name] = res.output
                _upstream_meta[name] = {
                    "ok": res.ok,
                    "degraded": res.degraded,
                    "error": res.error,
                }
                stdout = res.summary or "[agent runner ok]"
                if res.artifact_path:
                    stdout += f"\n→ {res.artifact_path}"
                return StepOutcome(
                    name=name,
                    kind=kind,
                    executed_script=f"agents/{name}",
                    returncode=0 if res.ok else 1,
                    stdout=stdout,
                    stderr=res.error,
                    duration_ms=res.duration_ms or int((_t.time() - t0) * 1000),
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("agent runner {} unavailable, fallback to script map: {}", name, e)

    # V1.21 真 skill runner 优先 (ROADMAP skill rollout 起点)
    # 与 expert runner 接口同, 仅 registry 独立 SKILL_RUNNERS
    if kind == "skill":
        try:
            from runtime.config.settings import get_settings
            from runtime.orchestrator.skills import get_skill_runner
            from runtime.orchestrator.agents.base import RunnerContext

            runner = get_skill_runner(name)
            if runner is not None:
                s = get_settings()
                ctx = RunnerContext(
                    artifact_text=inputs.get("artifact_text", ""),
                    upstream=dict(_upstream_outputs),
                    upstream_meta=dict(_upstream_meta),
                    settings_provider=s.llm_provider,
                    workspace=s.project_root / "workspace",
                    lang=inputs.get("lang", "zh"),
                    mode=inputs.get("mode", "exec"),
                )
                import time as _t
                t0 = _t.time()
                res = runner.run(ctx)
                _upstream_outputs[name] = res.output
                _upstream_meta[name] = {
                    "ok": res.ok,
                    "degraded": res.degraded,
                    "error": res.error,
                }
                stdout = res.summary or "[skill runner ok]"
                if res.artifact_path:
                    stdout += f"\n→ {res.artifact_path}"
                return StepOutcome(
                    name=name,
                    kind=kind,
                    executed_script=f"skills/{name}",
                    returncode=0 if res.ok else 1,
                    stdout=stdout,
                    stderr=res.error,
                    duration_ms=res.duration_ms or int((_t.time() - t0) * 1000),
                )
        except Exception as e:  # noqa: BLE001
            logger.warning("skill runner {} unavailable, fallback to script map: {}", name, e)

    # Fallback: SCRIPT_MAP(主宪章 §9 已有实现保留)
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
            stderr=f"script '{script}' not found under utils/",
            duration_ms=0,
        )
    defaults = SCRIPT_DEFAULT_ARGS.get(script, {})
    merged = {**defaults, **inputs}  # explicit inputs win
    for k, v in defaults.items():
        if k not in inputs:  # only materialize fixture for auto-injected defaults
            _ensure_fixture(str(v))
    # V1.14:`artifact_text` 给 AgentRunner 用,不当 CLI arg(多行文本会炸 argparse)
    _CLI_EXCLUDE = {"artifact_text", "lang", "mode"}
    args = [f"--{k}={v}" for k, v in merged.items() if k not in _CLI_EXCLUDE]
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
