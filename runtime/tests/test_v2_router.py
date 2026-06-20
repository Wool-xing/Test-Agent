"""Tests for IntentRouterV2."""

from __future__ import annotations

import pytest

from runtime.router.llm_client import LLMClient
from runtime.router.schema import DAGNode, RoutingDecision
from runtime.router.v2_router import IntentRouterV2, RouterV2Error


# ── Helpers ──────────────────────────────────────────────────────────────────


def _keyword_route(router: IntentRouterV2, target: str) -> RoutingDecision:
    """Route using keyword-based degraded mode (no LLM)."""
    return router._route_via_keywords(target, "cli")


_STUB = LLMClient(provider="stub", fallback="stub")


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def v2_router() -> IntentRouterV2:
    return IntentRouterV2()


# ── Catalog tests ───────────────────────────────────────────────────────────


def test_loads_all_48_manifests(v2_router: IntentRouterV2):
    """16 agents + 32 skills = 48 total manifests in specs/."""
    total = v2_router.agent_count + v2_router.skill_count
    assert v2_router.agent_count == 16, f"expected 16 agents, got {v2_router.agent_count}"
    assert v2_router.skill_count == 32, f"expected 32 skills, got {v2_router.skill_count}"
    assert total == 48, f"expected 48 total manifests, got {total}"


def test_catalog_has_core_agents(v2_router: IntentRouterV2):
    """Core 8 agents must be present."""
    core = {
        "requirements-analyst", "testcase-designer", "env-manager",
        "data-preparer", "automation-engineer", "test-executor",
        "bug-manager", "report-generator",
    }
    names = {e["name"] for e in v2_router._catalog["agents"]}
    missing = core - names
    assert not missing, f"missing core agents: {missing}"


def test_catalog_has_test_lead(v2_router: IntentRouterV2):
    """test-lead must be in the catalog."""
    names = {e["name"] for e in v2_router._catalog["agents"]}
    assert "test-lead" in names


def test_catalog_has_platform_agents(v2_router: IntentRouterV2):
    """5 platform extension agents must be present."""
    platform = {"mobile-tester", "desktop-tester", "visual-tester", "system-tester", "ai-tester"}
    names = {e["name"] for e in v2_router._catalog["agents"]}
    missing = platform - names
    assert not missing, f"missing platform agents: {missing}"


def test_catalog_has_vertical_agents(v2_router: IntentRouterV2):
    """2 vertical domain agents must be present."""
    vertical = {"pentest-tester", "automotive-tester"}
    names = {e["name"] for e in v2_router._catalog["agents"]}
    missing = vertical - names
    assert not missing, f"missing vertical agents: {missing}"


def test_catalog_has_key_skills(v2_router: IntentRouterV2):
    """Key skills should be present in the catalog."""
    key_skills = {
        "smoke-test", "test-coordinator", "e2e-testing", "regression-test",
        "mobile-test", "desktop-test", "visual-test", "system-test",
        "ai-test", "pentest-coordinator", "security-review",
    }
    names = {e["name"] for e in v2_router._catalog["skills"]}
    missing = key_skills - names
    assert not missing, f"missing key skills: {missing}"


# ── Keyword routing tests (no LLM, direct degraded mode) ─────────────────────


@pytest.mark.parametrize(
    ("target", "expected_type", "expected_expert"),
    [
        ("test a web system login flow", "web-system", "automation-engineer"),
        ("REST api with grpc endpoints", "rest-api", "automation-engineer"),
        ("APK Android 移动端测试", "mobile-app", "mobile-tester"),
        ("desktop windows exe app", "desktop-app", "desktop-tester"),
        ("AI LLM model evaluation", "ai-model", "ai-tester"),
        ("Canvas WebGL OCR 视觉回归 screenshot diff", "visual-system", "visual-tester"),
        ("IoT 嵌入式 MQTT Kafka 串口 modbus", "system-integration", "system-tester"),
        ("pentest SQL injection XSS SSRF OWASP 渗透测试", "pentest", "pentest-tester"),
        ("车载 ECU ADAS CAN-bus V2X OTA ASIL automotive", "automotive", "automotive-tester"),
    ],
)
def test_keyword_routing_platform_expert(
    v2_router: IntentRouterV2, target: str, expected_type: str, expected_expert: str
):
    """Keyword-based routing should pick the right platform expert."""
    decision = _keyword_route(v2_router, target)
    assert decision.detected_target_type == expected_type, (
        f"expected {expected_type}, got {decision.detected_target_type}"
    )
    names = [n.name for n in decision.dag]
    assert expected_expert in names, f"missing expert '{expected_expert}' in {names}"


def test_keyword_routing_starts_with_requirements_analyst(v2_router: IntentRouterV2):
    """DAG should start with requirements-analyst."""
    decision = _keyword_route(v2_router, "generic web system")
    ordered = decision.topological()
    assert ordered[0].name == "requirements-analyst", (
        f"first node should be requirements-analyst, got {ordered[0].name}"
    )


def test_keyword_routing_pentest_includes_coordinator_skill(v2_router: IntentRouterV2):
    """Pentest path should include pentest-coordinator skill as first node."""
    decision = _keyword_route(v2_router, "pentest SQL injection penetration test")
    ordered = decision.topological()
    assert ordered[0].name == "pentest-coordinator", (
        f"pentest head should be pentest-coordinator, got {ordered[0].name}"
    )
    assert ordered[0].kind == "skill", (
        f"pentest-coordinator kind should be skill, got {ordered[0].kind}"
    )


# ── Validation tests ────────────────────────────────────────────────────────


def test_validation_rejects_unknown_agent(v2_router: IntentRouterV2):
    """Validation should flag agents not in the ManifestV2 catalog."""
    decision = RoutingDecision(
        dag=[
            DAGNode(id="n0", kind="expert", name="nonexistent-agent", one_liner_zh="Unknown"),
        ],
        rationale="test",
        confidence=0.8,
        detected_target_type="web-system",
    )
    issues = v2_router._validate_decision(decision)
    assert len(issues) == 1
    assert "unknown" in issues[0] or "not found" in issues[0]
    assert "nonexistent-agent" in issues[0]


def test_validation_rejects_kind_mismatch(v2_router: IntentRouterV2):
    """Validation should flag when DAG says 'skill' but catalog says 'agent'."""
    # 'requirements-analyst' is an agent in the catalog, not a skill
    decision = RoutingDecision(
        dag=[
            DAGNode(id="n0", kind="skill", name="requirements-analyst", one_liner_zh="Mismatch"),
        ],
        rationale="test",
        confidence=0.8,
        detected_target_type="web-system",
    )
    issues = v2_router._validate_decision(decision)
    assert len(issues) == 1
    assert "kind mismatch" in issues[0]
    assert "requirements-analyst" in issues[0]


def test_validation_rejects_cycles(v2_router: IntentRouterV2):
    """Validation should detect DAG cycles."""
    decision = RoutingDecision(
        dag=[
            DAGNode(id="n0", kind="expert", name="test-lead", depends_on=["n1"], one_liner_zh="Leader"),
            DAGNode(id="n1", kind="expert", name="requirements-analyst", depends_on=["n0"], one_liner_zh="Analyst"),
        ],
        rationale="test",
        confidence=0.8,
        detected_target_type="web-system",
    )
    issues = v2_router._validate_decision(decision)
    cycle_issues = [i for i in issues if "cycle" in i.lower()]
    assert len(cycle_issues) == 1


def test_validation_passes_valid_decision(v2_router: IntentRouterV2):
    """A valid decision with known agents should pass validation."""
    decision = RoutingDecision(
        dag=[
            DAGNode(id="n0", kind="expert", name="requirements-analyst", one_liner_zh="Analyze"),
            DAGNode(id="n1", kind="expert", name="testcase-designer", depends_on=["n0"], one_liner_zh="Design"),
            DAGNode(id="n2", kind="expert", name="test-executor", depends_on=["n1"], one_liner_zh="Execute"),
        ],
        rationale="valid test routing",
        confidence=0.9,
        detected_target_type="web-system",
    )
    issues = v2_router._validate_decision(decision)
    assert len(issues) == 0, f"expected no issues, got: {issues}"


# ── RoutingDecision schema validation ────────────────────────────────────────


def test_routing_decision_schema_validates():
    """RoutingDecision should validate against its own Pydantic schema."""
    decision = RoutingDecision(
        dag=[
            DAGNode(id="n0", kind="expert", name="test-lead", one_liner_zh="Decide"),
        ],
        rationale="test",
        confidence=0.5,
        detected_target_type="web-system",
    )
    validated = RoutingDecision.model_validate(decision.model_dump())
    assert validated.confidence == 0.5
    assert len(validated.dag) == 1


def test_routing_decision_rejects_empty_dag():
    """RoutingDecision should reject invalid DAG via topology check."""
    with pytest.raises(ValueError):
        RoutingDecision(
            dag=[
                DAGNode(id="n0", kind="expert", name="test-lead", depends_on=["n99"], one_liner_zh="Bad"),
            ],
            rationale="test",
            confidence=0.5,
            detected_target_type="web-system",
        ).topological()


def test_plan_only_returns_decision(v2_router: IntentRouterV2):
    """plan_only should return a RoutingDecision."""
    decision = v2_router.plan_only("test the login API")
    assert isinstance(decision, RoutingDecision)
    assert len(decision.dag) > 0
    assert decision.confidence > 0.0


# ── Degraded mode ──────────────────────────────────────────────────────────


def test_keyword_routing_handles_empty_target(v2_router: IntentRouterV2):
    """Empty target should still produce a valid default routing."""
    decision = _keyword_route(v2_router, "")
    assert isinstance(decision, RoutingDecision)
    assert len(decision.dag) > 0


def test_keyword_routing_returns_default_for_unknown(v2_router: IntentRouterV2):
    """Completely unknown target type should fall back to web-system default."""
    decision = _keyword_route(v2_router, "xyzzy something completely random")
    assert decision.detected_target_type == "web-system", (
        f"expected web-system, got {decision.detected_target_type}"
    )
    names = [n.name for n in decision.dag]
    assert "requirements-analyst" in names


def test_full_route_with_stub_uses_keyword_fallback(v2_router: IntentRouterV2):
    """Full route() with stub client should fall back to keyword routing."""
    decision = v2_router.route("APK Android app testing", client=_STUB)
    assert decision.detected_target_type == "mobile-app"
    names = [n.name for n in decision.dag]
    assert "mobile-tester" in names


# ── DAGNode schema ──────────────────────────────────────────────────────────


def test_dag_node_requires_nonempty_id():
    with pytest.raises(ValueError):
        DAGNode(id="", kind="expert", name="test-lead")


def test_dag_node_requires_nonempty_name():
    with pytest.raises(ValueError):
        DAGNode(id="n0", kind="expert", name="")


def test_dag_node_defaults():
    node = DAGNode(id="n0", kind="expert", name="test-lead")
    assert node.depends_on == []
    assert node.dep_mode == "hard"
    assert node.on_failure == "retry"
    assert node.timeout_seconds == 1800
