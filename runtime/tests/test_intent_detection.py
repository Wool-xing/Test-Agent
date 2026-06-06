"""TDD: Sub-agent intent detection and direct invocation."""

from __future__ import annotations

import pytest


class TestDetectDirectAgent:
    """Test agent/skill name detection in user input."""

    @pytest.fixture(autouse=True)
    def _prime_catalog(self):
        """Ensure catalog is loaded before tests."""
        try:
            from runtime.registry.registry import get_catalog
            get_catalog(refresh=True)
        except Exception:
            pass

    def test_at_mention_agent(self):
        from runtime.router.intent import detect_direct_agent

        targets = detect_direct_agent("请 @test-lead 帮我分析这个需求")
        assert len(targets) > 0
        names = {n for n, _ in targets}
        assert "test-lead" in names or any("test" in n for n in names)

    def test_cn_use_agent(self):
        from runtime.router.intent import detect_direct_agent

        targets = detect_direct_agent("用 pentest-tester 扫描 example.com")
        names = {n for n, _ in targets}
        assert "pentest-tester" in names

    def test_cn_use_variant(self):
        from runtime.router.intent import detect_direct_agent

        for phrase in ["使用", "调用", "通过", "借助"]:
            targets = detect_direct_agent(f"{phrase} requirements-analyst 分析PRD")
            names = {n for n, _ in targets}
            assert "requirements-analyst" in names, f"Failed for '{phrase}'"

    def test_en_use_agent(self):
        from runtime.router.intent import detect_direct_agent

        targets = detect_direct_agent("use smoke-test to verify the build")
        names = {n for n, _ in targets}
        assert "smoke-test" in names

    def test_en_variants(self):
        from runtime.router.intent import detect_direct_agent

        for verb in ["run", "invoke", "call", "trigger"]:
            targets = detect_direct_agent(f"{verb} bug-manager for this issue")
            names = {n for n, _ in targets}
            assert "bug-manager" in names, f"Failed for '{verb}'"

    def test_no_agent_mentioned(self):
        from runtime.router.intent import detect_direct_agent

        targets = detect_direct_agent("帮我测试一下登录页面")
        assert len(targets) == 0  # no explicit agent mention

    def test_multiple_agents(self):
        from runtime.router.intent import detect_direct_agent

        targets = detect_direct_agent("用 requirements-analyst 分析，然后 @smoke-test 验证")
        names = {n for n, _ in targets}
        # At least one should be found
        assert len(targets) >= 1

    def test_empty_text(self):
        from runtime.router.intent import detect_direct_agent

        targets = detect_direct_agent("")
        assert len(targets) == 0

    def test_unknown_agent_ignored(self):
        from runtime.router.intent import detect_direct_agent

        targets = detect_direct_agent("用 nonexistent-agent-xyz 测试")
        assert len(targets) == 0

    def test_partial_name_no_match(self):
        from runtime.router.intent import detect_direct_agent

        # "test" alone is too short and also a common word
        targets = detect_direct_agent("用 test 测试")
        assert len(targets) == 0  # "test" is not a registered name


class TestBuildDirectDAG:
    """Test direct DAG construction from matched targets."""

    def test_single_target_creates_dag(self):
        from runtime.router.intent import build_direct_dag

        decision = build_direct_dag([("test-lead", "expert")])
        assert decision is not None
        assert len(decision.dag) == 1
        assert decision.dag[0].name == "test-lead"
        assert decision.dag[0].kind == "expert"
        assert decision.confidence == 0.9

    def test_multiple_targets_chain(self):
        from runtime.router.intent import build_direct_dag

        decision = build_direct_dag([
            ("requirements-analyst", "expert"),
            ("smoke-test", "skill"),
        ])
        assert decision is not None
        assert len(decision.dag) == 2
        # Second node depends on first
        assert decision.dag[1].depends_on == [decision.dag[0].id]

    def test_empty_targets_returns_none(self):
        from runtime.router.intent import build_direct_dag

        decision = build_direct_dag([])
        assert decision is None

    def test_artifact_text_passed(self):
        from runtime.router.intent import build_direct_dag

        decision = build_direct_dag(
            [("test-lead", "expert")],
            artifact_text="test the login feature for security bugs",
        )
        assert decision is not None
        assert "test the login" in decision.dag[0].inputs.get("artifact_text", "")

    def test_custom_confidence(self):
        from runtime.router.intent import build_direct_dag

        decision = build_direct_dag(
            [("test-lead", "expert")],
            confidence=0.95,
        )
        assert decision is not None
        assert decision.confidence == 0.95


class TestTryFastPath:
    """Test the main entry point: try_fast_path()."""

    @pytest.fixture(autouse=True)
    def _prime_catalog(self):
        try:
            from runtime.registry.registry import get_catalog
            get_catalog(refresh=True)
        except Exception:
            pass

    def test_direct_agent_path(self):
        from runtime.router.intent import try_fast_path

        decision = try_fast_path("@test-lead 分析这个需求")
        assert decision is not None
        assert len(decision.dag) >= 1

    def test_no_agent_falls_through(self):
        from runtime.router.intent import try_fast_path

        decision = try_fast_path("regular text without agent names")
        assert decision is None  # fall through to LLM router


class TestBridgeMemoryKey:
    """Test IM conversation memory key generation."""

    def test_memory_key_format(self):
        from runtime.gateway.bridge import _memory_key

        key = _memory_key("telegram", "user123", "chat456")
        assert key == "telegram:user123:chat456"

    def test_memory_key_anon(self):
        from runtime.gateway.bridge import _memory_key

        key = _memory_key("discord", None, None)
        assert "anon" in key
        assert "discord" in key

    def test_memory_key_different_users(self):
        from runtime.gateway.bridge import _memory_key

        key1 = _memory_key("telegram", "alice", "room1")
        key2 = _memory_key("telegram", "bob", "room1")
        assert key1 != key2
