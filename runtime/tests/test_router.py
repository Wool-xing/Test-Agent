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
    ],
)
def test_router_picks_platform_expert(text, expected_type, expected_expert):
    art = TargetArtifact(kind="text", text=text)
    client = LLMClient(provider="stub", fallback="stub")
    decision = route(art, client=client)
    assert decision.detected_target_type == expected_type
    names = [n.name for n in decision.dag]
    assert expected_expert in names, f"missing {expected_expert} in {names}"


def test_router_starts_with_requirements_analyst():
    art = TargetArtifact(kind="text", text="generic web system")
    decision = route(art, client=LLMClient(provider="stub", fallback="stub"))
    ordered = decision.topological()
    assert ordered[0].name == "requirements-analyst"


def test_router_ends_with_report_generator():
    art = TargetArtifact(kind="text", text="generic web system")
    decision = route(art, client=LLMClient(provider="stub", fallback="stub"))
    ordered = decision.topological()
    assert ordered[-1].name == "report-generator"
