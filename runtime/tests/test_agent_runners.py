"""9 个 LLM-driven AgentRunner 专项 unit test (V1.16-followup).

覆盖 3 维度 × 9 runner = 27 case (参数化):
- registration: @register("name") + __init__.py import 双链路 → get_runner(name) 非空
  (防 __init__.py 漏 import 致 silent fallback no-op)
- mock_output schema: 必填 top-level keys 全在
  (schema regression 即时 catch, 不依赖运行时 mock 调用)
- summary 非空: 一行业务摘要存在
  (防 summary 改空 regression, report-generator 下游消费)

模板规则锁定 (V1.17+ 新 AgentRunner 必填):
- 加 1 runner → 更新 ALL_RUNNERS 加 1 行 (name, required_keys)
- 不加 → 参数化漏覆盖, pytest 不报错但 silent gap

参考 LangChain agents / CrewAI / AutoGen 单元测试模式: mock LLM (stub provider 替代真调用) +
验 output schema + 验 registration。
"""

from __future__ import annotations

import pytest

from runtime.orchestrator.agents import AGENT_RUNNERS, get_runner
from runtime.orchestrator.agents.base import RunnerContext

# (runner name, required mock_output top-level keys) — 与各 runner .py mock_output 对齐
# 不含下划线开头字段 (e.g., _mode 是 stub 标志, 非业务字段)
ALL_RUNNERS: list[tuple[str, list[str]]] = [
    (
        "requirements-analyst",
        ["project_name", "features", "business_rules", "risk_areas", "non_functional", "out_of_scope", "confidence"],
    ),
    (
        "automation-engineer",
        ["scripts", "fixtures_shared", "skip_reasons", "estimated_effort_hours"],
    ),
    (
        "test-executor",
        ["execution_plan", "failure_classification_rules", "flaky_detection", "estimated_total_minutes"],
    ),
    (
        "bug-manager",
        ["bugs", "tracker", "submit_strategy", "summary"],
    ),
    (
        "test-lead",
        ["verdict", "rationale", "metrics", "known_risks", "fallback_plan", "summary_zh", "requires_human_signoff", "signoff_owner"],
    ),
    (
        "env-manager",  # V1.15.0-alpha
        ["project_name", "target_env", "env_checks", "prep_steps", "dependencies", "risks", "confidence"],
    ),
    (
        "mobile-tester",  # V1.16.0-alpha
        ["project_name", "target_platform", "test_cases", "device_commands", "test_environment", "mobile_specific", "risks", "confidence"],
    ),
    (
        "visual-tester",  # V1.17.0-alpha
        ["project_name", "visual_target_type", "visual_test_points", "comparison_scripts", "tolerance", "baseline_strategy", "risks", "confidence"],
    ),
    (
        "system-tester",  # V1.18.0-alpha
        ["project_name", "system_target_type", "test_cases", "device_commands", "protocol_specific", "test_environment", "risks", "confidence"],
    ),
]


# pytest id 函数 — 让失败时报 runner 名而非 index
def _runner_id(case: tuple[str, list[str]]) -> str:
    return case[0]


@pytest.mark.parametrize("case", ALL_RUNNERS, ids=_runner_id)
def test_runner_registered(case: tuple[str, list[str]]) -> None:
    """get_runner(name) 必须返非 None。

    失败 = @register("name") + __init__.py import 链路断了 → execute_node 会 silent
    fallback 到 SCRIPT_MAP no-op, 用户路由不报错但 runner 没真跑。
    """
    name, _ = case
    runner = get_runner(name)
    assert runner is not None, (
        f"{name} 不在 AGENT_RUNNERS — 检查 runtime/orchestrator/agents/__init__.py 是否 import "
        f"对应 module 触发 @register"
    )


@pytest.mark.parametrize("case", ALL_RUNNERS, ids=_runner_id)
def test_runner_mock_schema(case: tuple[str, list[str]]) -> None:
    """mock_output 必填 top-level keys 全在 (selftest --e2e + stub mode 兜底依赖此 schema)。"""
    name, required_keys = case
    runner = get_runner(name)
    assert runner is not None  # 已被 test_runner_registered 保
    # 给 dependent runners 提供 fake upstream 避免 KeyError
    ctx = RunnerContext(
        artifact_text="测试 PRD",
        settings_provider="stub",
        upstream={
            "requirements-analyst": {
                "features": [{"name": "login", "priority": "P0"}],
                "non_functional": {},
                "business_rules": [],
            },
            "automation-engineer": {"scripts": []},
            "test-executor": {"execution_plan": []},
            "bug-manager": {},
            "env-manager": {},
        },
    )
    out = runner.mock_output(ctx)
    missing = [k for k in required_keys if k not in out]
    assert not missing, f"{name} mock_output 缺必填 keys: {missing} (实有: {sorted(out.keys())})"


@pytest.mark.parametrize("case", ALL_RUNNERS, ids=_runner_id)
def test_runner_summary_non_empty(case: tuple[str, list[str]]) -> None:
    """summary() 返非空字符串 (report-generator / test-lead 下游消费一行摘要)。"""
    name, _ = case
    runner = get_runner(name)
    assert runner is not None
    ctx = RunnerContext(
        artifact_text="测试 PRD",
        settings_provider="stub",
        upstream={
            "requirements-analyst": {
                "features": [{"name": "login", "priority": "P0"}],
                "non_functional": {},
                "business_rules": [],
            },
            "automation-engineer": {"scripts": []},
            "test-executor": {"execution_plan": []},
            "bug-manager": {},
            "env-manager": {},
        },
    )
    out = runner.mock_output(ctx)
    s = runner.summary(out)
    assert isinstance(s, str), f"{name} summary 应返 str, 实 {type(s).__name__}"
    assert s.strip(), f"{name} summary 空 (report-generator 下游消费会出 placeholder)"


# 锚: ALL_RUNNERS 与 AGENT_RUNNERS 同步 — 防新加 runner 漏更新此清单
def test_all_runners_covers_agent_runners_registry() -> None:
    """ALL_RUNNERS 必须覆盖 AGENT_RUNNERS 所有 key (新 runner 加入后必更新此清单)。"""
    covered = {name for name, _ in ALL_RUNNERS}
    registered = set(AGENT_RUNNERS.keys())
    missing_from_test = registered - covered
    extra_in_test = covered - registered
    assert not missing_from_test, (
        f"AGENT_RUNNERS 含但 ALL_RUNNERS 缺: {missing_from_test} "
        f"— 新加 runner 必更新 test_agent_runners.py 的 ALL_RUNNERS"
    )
    assert not extra_in_test, (
        f"ALL_RUNNERS 含但 AGENT_RUNNERS 缺: {extra_in_test} "
        f"— 已删除 runner 残留, 应同步清掉"
    )
