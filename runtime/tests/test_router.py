"""Router smoke tests against catalog using the stub LLM provider."""

from __future__ import annotations

import pytest

from runtime.router.llm_client import LLMClient
from runtime.router.router import route
from runtime.router.schema import TargetArtifact


@pytest.mark.parametrize(
    ("text", "expected_type", "expected_expert"),
    [
        ("test a web system https://example.com login flow", "web-system", "automation-engineer"),
        ("REST api with grpc endpoints to validate", "rest-api", "automation-engineer"),
        ("我有一个 APK 文件需要做 Android 移动端测试", "mobile-app", "mobile-tester"),
        ("desktop windows exe app", "desktop-app", "desktop-tester"),
        ("AI LLM model evaluation", "ai-model", "ai-tester"),
        ("Canvas WebGL OCR 视觉回归 screenshot diff", "visual-system", "visual-tester"),
        ("IoT 嵌入式 MQTT Kafka Jaeger 串口 modbus", "system-integration", "system-tester"),
        ("pentest SQL injection XSS SSRF OWASP 渗透测试", "pentest", "pentest-tester"),
        ("车载 ECU ADAS CAN-bus V2X OTA ASIL automotive", "automotive", "automotive-tester"),
    ],
)
def test_router_picks_platform_expert(text, expected_type, expected_expert):
    art = TargetArtifact(kind="text", text=text)
    client = LLMClient(provider="stub", fallback="stub")
    decision = route(art, client=client)
    assert decision.detected_target_type == expected_type
    names = [n.name for n in decision.dag]
    assert expected_expert in names, f"missing {expected_expert} in {names}"


def test_router_pentest_includes_coordinator_skill():
    """pentest path 头节点 = pentest-coordinator (kind=skill, SkillRunner 首接入)."""
    art = TargetArtifact(kind="text", text="pentest SQL injection penetration test")
    decision = route(art, client=LLMClient(provider="stub", fallback="stub"))
    ordered = decision.topological()
    assert ordered[0].name == "pentest-coordinator", f"pentest 头节点应 pentest-coordinator, 实 {ordered[0].name}"
    assert ordered[0].kind == "skill", f"pentest-coordinator kind 应 skill, 实 {ordered[0].kind}"


def test_router_starts_with_requirements_analyst():
    art = TargetArtifact(kind="text", text="generic web system")
    decision = route(art, client=LLMClient(provider="stub", fallback="stub"))
    ordered = decision.topological()
    assert ordered[0].name == "requirements-analyst"


def test_router_ends_with_test_lead_decision():
    """DAG 末节点 = test-lead 决策(agents/README.md 流程
    "bug-manager → report-generator → test-lead 决策")。report-generator 倒数第二。"""
    art = TargetArtifact(kind="text", text="generic web system")
    decision = route(art, client=LLMClient(provider="stub", fallback="stub"))
    ordered = decision.topological()
    assert ordered[-1].name == "test-lead", f"DAG 末节点应 test-lead 决策, 实 {ordered[-1].name}"
    assert ordered[-2].name == "report-generator", f"末-1 应 report-generator, 实 {ordered[-2].name}"
