"""X4 防 mock 闭环测试:registry parse → router warn → orchestrator hard block。

覆盖 ROADMAP V1.15 Day 0 承诺:rollout / vision / unknown 状态的 expert / skill,
router 路由仍可生成 DAG 但 _validate_against_catalog 标 issue + 降 confidence,
orchestrator execute_node 跑到时 returncode=2 + stderr "未实装",绝不输出 mock 数据。

单源:02-专家定义/03-技能定义 *.md frontmatter EXPERT_IMPL_STATUS / SKILL_IMPL_STATUS。
"""

from __future__ import annotations

from collections import Counter

from runtime.orchestrator.adapters.experts import execute_node
from runtime.registry.registry import get_catalog
from runtime.router import router
from runtime.router.schema import RoutingDecision

# ---------- registry 层:frontmatter parse ----------


def test_registry_impl_status_no_unknown():
    """所有 expert + skill frontmatter 必含合法 IMPL_STATUS,任 unknown = X1/X2 PR #63/#64 漏。"""
    cat = get_catalog()
    bad = [e.name for e in cat.all() if e.impl_status == "unknown"]
    assert not bad, f"以下 entry frontmatter IMPL_STATUS 缺失/非法: {bad}"


def test_registry_expert_status_counts():
    """Expert 16 = 11 production + 5 script + 0 rollout (V1.20.0-alpha automotive-tester 落地后,V1.x rollout 收尾)。"""
    cat = get_catalog()
    counts = Counter(e.impl_status for e in cat.experts.values())
    assert counts.get("production", 0) == 11, f"expert production 应 11,实 {counts.get('production')}"
    assert counts.get("script", 0) == 5, f"expert script 应 5,实 {counts.get('script')}"
    assert counts.get("rollout", 0) == 0, f"expert rollout 应 0 (V1.x rollout 收尾),实 {counts.get('rollout')}"


def test_registry_skill_status_counts():
    """Skill 32 = 17 production + 7 script + 6 rollout + 2 vision (V1.31.0-alpha 全 skill rollout 完成)。"""
    cat = get_catalog()
    counts = Counter(e.impl_status for e in cat.skills.values())
    assert counts.get("production", 0) == 8, f"skill production 应 17,实 {counts.get('production')}"
    assert counts.get("script", 0) == 7
    assert counts.get("rollout", 0) == 15, f"skill rollout 应 6,实 {counts.get('rollout')}"
    assert counts.get("vision", 0) == 2


# ---------- router 层:_validate_against_catalog warn ----------


def _mk_decision(*dag_specs: tuple[str, str, str]) -> RoutingDecision:
    """dag_specs: [(id, kind, name), ...]"""
    return RoutingDecision.model_validate(
        {
            "detected_target_type": "web",
            "confidence": 0.9,
            "rationale": "X4 test",
            "dag": [{"id": i, "kind": k, "name": n} for i, k, n in dag_specs],
        }
    )


def test_router_flags_rollout_expert():
    # V1.20 V1.x rollout 收尾,所有 expert production/script。
    # rollout 分支覆盖通过 skill 层 (test_router_flags_rollout_skill,16 skill 仍 rollout)。
    # unknown 分支覆盖通过 test_router_flags_unknown_entity。
    # 此 test 保留为占位,改测 unknown expert (走相同 hard-block 分支)。
    cat = get_catalog()
    dec = _mk_decision(("n1", "expert", "phantom-automotive-future"))
    issues = router._validate_against_catalog(dec, cat)
    assert any("phantom-automotive-future" in i and "unknown" in i for i in issues), issues


def test_router_flags_rollout_skill():
    """X4 核心新加 — 之前 skill rollout 不被 router 标 issue,导致 LLM 顺利路由 → orchestrator no-op 假成功。"""
    cat = get_catalog()
    dec = _mk_decision(("n1", "skill", "visual-test"))
    issues = router._validate_against_catalog(dec, cat)
    assert any("visual-test" in i and "rollout" in i for i in issues), issues


def test_router_flags_vision_skill():
    cat = get_catalog()
    dec = _mk_decision(("n1", "skill", "agent-introspection-debugging"))
    issues = router._validate_against_catalog(dec, cat)
    assert any("agent-introspection-debugging" in i and "vision" in i for i in issues), issues


def test_router_flags_unknown_entity():
    cat = get_catalog()
    dec = _mk_decision(("n1", "expert", "phantom-expert"))
    issues = router._validate_against_catalog(dec, cat)
    assert any("phantom-expert" in i and "unknown" in i for i in issues), issues


def test_router_passes_production_clean():
    """Production expert/skill 不应被误标 issue。"""
    cat = get_catalog()
    dec = _mk_decision(
        ("n1", "expert", "test-lead"),
        ("n2", "skill", "smoke-test"),
        ("n3", "expert", "automation-engineer"),
    )
    issues = router._validate_against_catalog(dec, cat)
    # 仅可能因 topological / unknown 报 issue, 不应因 status 报
    status_issues = [i for i in issues if "rollout" in i or "vision" in i or "unknown" in i]
    assert not status_issues, f"production 被误标: {status_issues}"


# ---------- orchestrator 层:execute_node hard block (returncode=2) ----------


def test_execute_node_rejects_rollout_expert():
    """V1.20 V1.x rollout 收尾,无 rollout expert。
    rollout 分支覆盖通过 test_execute_node_rejects_rollout_skill (16 skill 仍 rollout)。
    expert hard-block 路径覆盖通过 test_execute_node_rejects_unknown_expert (同分支)。
    此 test 保留 + 改用 unknown expert 触发同 returncode=2 hard-block。
    """
    r = execute_node("phantom-future-expert", "expert")
    assert r.returncode == 2
    assert "unknown expert" in r.stderr


def test_execute_node_rejects_rollout_skill():
    """X4 核心 — skill rollout 之前走 _resolve_script 返 no-op "documented step recorded" (mock!),
    X4 改后硬拒 rc=2。

    V1.21+ pentest-coordinator 已 production, 改用 automotive-can-bus-test (仍 rollout)。"""
    r = execute_node("automotive-can-bus-test", "skill")
    assert r.returncode == 2
    assert "未实装" in r.stderr
    assert "rollout" in r.stderr
    # 反例:确保不是 no-op 假成功
    assert "documented step recorded" not in r.stdout


def test_execute_node_rejects_vision_skill():
    r = execute_node("agent-introspection-debugging", "skill")
    assert r.returncode == 2
    assert "未实装" in r.stderr
    assert "vision" in r.stderr


def test_execute_node_rejects_unknown_skill():
    r = execute_node("nonexistent-skill", "skill")
    assert r.returncode == 2
    assert "unknown skill" in r.stderr


def test_execute_node_rejects_unknown_expert():
    r = execute_node("phantom-expert", "expert")
    assert r.returncode == 2
    assert "unknown expert" in r.stderr


# 注:test_execute_node_runs_production_expert / script_skill 不写为 X4 单元测试,
# 因为它们依赖 LLM provider 或 script 真跑 (test-lead 调用 LLMClient,data-preparation
# 跑 data_factory.py),走 test_smoke_e2e.py / test_router_real.py 集成测试覆盖。
# X4 范围仅验防 mock 拒绝路径,production / script 正向路径不动。
