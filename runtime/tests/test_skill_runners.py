"""LLM-driven SkillRunner 专项 unit test.

照 test_agent_runners.py pattern 同构:
覆盖 3 维度 × N skill_runner = 3N case (参数化):
- registration: @register_skill("name") + skills/__init__.py import 双链路 → get_skill_runner(name) 非空
  (防 __init__.py 漏 import 致 silent fallback no-op)
- mock_output schema: 必填 top-level keys 全在
  (schema regression 即时 catch)
- summary 非空: 一行业务摘要存在
  (防 summary 改空 regression, report-generator 下游消费)

模板规则锁定 :
- 加 1 skill_runner → 更新 ALL_SKILL_RUNNERS 加 1 行 (name, required_keys)
- 不加 → 参数化漏覆盖, pytest 不报错但 silent gap
"""

from __future__ import annotations

import pytest

from runtime.orchestrator.agents.base import RunnerContext
from runtime.orchestrator.skills import SKILL_RUNNERS, get_skill_runner

# (skill name, required mock_output top-level keys) — 与各 skill .py mock_output 对齐
# 不含下划线开头字段 (e.g., _mode 是 stub 标志, 非业务字段)
ALL_SKILL_RUNNERS: list[tuple[str, list[str]]] = [
    (
        "pentest-coordinator", # (skill rollout 起点)
        [
            "project_name",
            "run_id",
            "authorization_check",
            "phases",
            "subagent_pool",
            "outputs",
            "refuse_conditions",
            "risks",
            "confidence",
        ],
    ),
    (
        "pentest-exploit",
        ["project_name","run_id","sandbox","domains","outputs","risks","confidence"],
    ),
    (
        "pentest-api",
        ["project_name","run_id","api_categories","openapi_driven","outputs","risks","confidence"],
    ),
    (
        "pentest-web",
        ["project_name","run_id","owasp_categories","auth_auto","outputs","risks","confidence"],
    ),
    (
        "pentest-report",
        ["project_name","run_id","sections","findings","pii_scrub","outputs","risks","confidence"],
    ),
    (
        "pentest-recon", #
        ["project_name","run_id","target","authorization","outputs","risks","confidence"],
    ),
    (
        "pentest-vuln", #
        ["project_name","run_id","source_available","mode","domains","outputs","risks","confidence"],
    ),
    (
        "mobile-test", #
        ["project_name","run_id","target_platform","phases","outputs","risks","confidence"],
    ),
    (
        "visual-test", #
        ["project_name","run_id","visual_target_type","phases","outputs","risks","confidence"],
    ),
    (
        "system-test", #
        ["project_name","run_id","sub_scenarios","phases","outputs","risks","confidence"],
    ),
    (
        "eval-harness", #
        ["project_name","run_id","eval_target","model_version","baseline_version","safety_checks","outputs","risks","confidence"],
    ),
    (
        "automotive-test", #
        ["project_name","run_id","vehicle_subsystem","asil_level","phases","sub_skills","outputs","risks","confidence"],
    ),
    (
        "automotive-can-bus-test", #
        ["project_name","run_id","protocols","checks","outputs","risks","confidence"],
    ),
    (
        "automotive-adas-scenario", #
        ["project_name","run_id","categories","odd_levels","simulation","outputs","risks","confidence"],
    ),
    (
        "automotive-ota-update-test", #
        ["project_name","run_id","checks","compliance","outputs","risks","confidence"],
    ),
    (
        "automotive-hil-loop-test", #
        ["project_name","run_id","loops","asil_required","fault_injection","platform","outputs","risks","confidence"],
    ),
    (
        "agent-introspection-debugging", #
        ["project_name","run_id","target_run_id","dimensions","findings","recommendations","outputs","confidence"],
    ),
    (
        "build-your-own-x-explorer", #
        ["project_name","run_id","user_scenario","detected_concepts","recommendations","warnings","outputs","confidence"],
    ),
]


def _skill_id(case: tuple[str, list[str]]) -> str:
    return case[0]


@pytest.mark.parametrize("case", ALL_SKILL_RUNNERS, ids=_skill_id)
def test_skill_runner_registered(case: tuple[str, list[str]]) -> None:
    """get_skill_runner(name) 必须返非 None。

    失败 = @register_skill("name") + __init__.py import 链路断了 → execute_node 会 silent
    fallback 到 SCRIPT_MAP no-op, 用户路由不报错但 skill runner 没真跑。
    """
    name, _ = case
    runner = get_skill_runner(name)
    assert runner is not None, (
        f"{name} 不在 SKILL_RUNNERS — 检查 runtime/orchestrator/skills/__init__.py 是否 import "
        f"对应 module 触发 @register_skill"
    )


@pytest.mark.parametrize("case", ALL_SKILL_RUNNERS, ids=_skill_id)
def test_skill_runner_mock_schema(case: tuple[str, list[str]]) -> None:
    """mock_output 必填 top-level keys 全在 (selftest --e2e + stub mode 兜底依赖此 schema)。"""
    name, required_keys = case
    runner = get_skill_runner(name)
    assert runner is not None
    ctx = RunnerContext(
        artifact_text="测试 PRD",
        settings_provider="stub",
        upstream={
            "requirements-analyst": {
                "features": [{"name": "auth", "priority": "P0"}],
                "non_functional": {},
            },
            "pentest-tester": {
                "target_scope": {
                    "in_scope": ["https://staging.example.com"],
                    "out_of_scope": ["https://prod.example.com"],
                },
                "test_mode": "graybox",
            },
        },
    )
    out = runner.mock_output(ctx)
    missing = [k for k in required_keys if k not in out]
    assert not missing, f"{name} mock_output 缺必填 keys: {missing} (实有: {sorted(out.keys())})"


@pytest.mark.parametrize("case", ALL_SKILL_RUNNERS, ids=_skill_id)
def test_skill_runner_summary_non_empty(case: tuple[str, list[str]]) -> None:
    """summary() 返非空字符串 (report-generator / test-lead 下游消费一行摘要)。"""
    name, _ = case
    runner = get_skill_runner(name)
    assert runner is not None
    ctx = RunnerContext(
        artifact_text="测试 PRD",
        settings_provider="stub",
        upstream={
            "requirements-analyst": {"features": [], "non_functional": {}},
            "pentest-tester": {"target_scope": {}, "test_mode": "graybox"},
        },
    )
    out = runner.mock_output(ctx)
    s = runner.summary(out)
    assert isinstance(s, str), f"{name} summary 应返 str, 实 {type(s).__name__}"
    assert s.strip(), f"{name} summary 空 (report-generator 下游消费会出 placeholder)"


# 锚: ALL_SKILL_RUNNERS 与 SKILL_RUNNERS 同步 — 防新加 skill_runner 漏更新此清单
def test_all_skill_runners_covers_registry() -> None:
    """ALL_SKILL_RUNNERS 必须覆盖 SKILL_RUNNERS 所有 key (新加 skill runner 后必更新此清单)。"""
    covered = {name for name, _ in ALL_SKILL_RUNNERS}
    registered = set(SKILL_RUNNERS.keys())
    missing_from_test = registered - covered
    extra_in_test = covered - registered
    assert not missing_from_test, (
        f"SKILL_RUNNERS 含但 ALL_SKILL_RUNNERS 缺: {missing_from_test} "
        f"— 新加 skill runner 必更新 test_skill_runners.py 的 ALL_SKILL_RUNNERS"
    )
    assert not extra_in_test, (
        f"ALL_SKILL_RUNNERS 含但 SKILL_RUNNERS 缺: {extra_in_test} "
        f"— 已删除 skill runner 残留, 应同步清掉"
    )
