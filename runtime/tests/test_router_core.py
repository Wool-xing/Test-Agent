"""TDD tests for runtime/router/ pure-logic modules:
schema, intent, llm_cache, prompt, model_router.

Target: boost runtime/router/ coverage from 33% toward 55%.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ═══════════════════════════════════════════════════════════════════════════
# schema.py — DAGNode, RoutingDecision, TargetArtifact, topological sort
# ═══════════════════════════════════════════════════════════════════════════

class TestDAGNode:
    def test_node_creation_minimal(self):
        """DAGNode should create with minimal fields."""
        from runtime.router.schema import DAGNode
        node = DAGNode(id="n0", kind="expert", name="测试主管")
        assert node.id == "n0"
        assert node.kind == "expert"
        assert node.name == "测试主管"
        assert node.depends_on == []
        assert node.dep_mode == "hard"
        assert node.on_failure == "retry"
        assert node.timeout_seconds == 1800

    def test_node_creation_full(self):
        """DAGNode should accept all optional fields."""
        from runtime.router.schema import DAGNode
        node = DAGNode(
            id="n1",
            kind="skill",
            name="smoke-test",
            depends_on=["n0"],
            dep_mode="soft",
            inputs={"url": "https://example.com"},
            on_failure="skip",
            timeout_seconds=600,
            one_liner_zh="运行冒烟测试",
            one_liner_en="Run smoke test",
            why="P0 coverage for login flow",
            theory_refs=["pytest", "shift-left"],
            alternatives=[{"name": "e2e-test", "rejected": "too slow for smoke"}],
        )
        assert node.one_liner_zh == "运行冒烟测试"
        assert len(node.theory_refs) == 2
        assert len(node.alternatives) == 1

    def test_node_empty_id_fails(self):
        """DAGNode with empty id should fail validation."""
        from pydantic import ValidationError

        from runtime.router.schema import DAGNode
        with pytest.raises(ValidationError):
            DAGNode(id="", kind="expert", name="test")

    def test_node_whitespace_id_fails(self):
        """DAGNode with whitespace-only id should fail."""
        from pydantic import ValidationError

        from runtime.router.schema import DAGNode
        with pytest.raises(ValidationError):
            DAGNode(id="   ", kind="expert", name="test")

    def test_node_empty_name_fails(self):
        """DAGNode with empty name should fail validation."""
        from pydantic import ValidationError

        from runtime.router.schema import DAGNode
        with pytest.raises(ValidationError):
            DAGNode(id="n0", kind="expert", name="")

    def test_node_defaults_are_distinct(self):
        """Each node instance should have its own default lists."""
        from runtime.router.schema import DAGNode
        n1 = DAGNode(id="n1", kind="expert", name="a")
        n2 = DAGNode(id="n2", kind="expert", name="b")
        n1.depends_on.append("n0")
        assert n2.depends_on == []


class TestRoutingDecision:
    def test_decision_creation(self):
        """RoutingDecision should wrap DAG nodes + metadata."""
        from runtime.router.schema import DAGNode, RoutingDecision
        nodes = [
            DAGNode(id="n0", kind="expert", name="需求分析"),
            DAGNode(id="n1", kind="skill", name="smoke-test", depends_on=["n0"]),
        ]
        dec = RoutingDecision(
            dag=nodes,
            rationale="Standard smoke test pipeline",
            confidence=0.95,
            detected_target_type="web-system",
            detected_qualities=["functional", "performance"],
        )
        assert len(dec.dag) == 2
        assert dec.confidence == 0.95

    def test_decision_duplicate_ids_fails(self):
        """RoutingDecision with duplicate DAG node IDs should fail."""
        from pydantic import ValidationError

        from runtime.router.schema import DAGNode, RoutingDecision
        nodes = [
            DAGNode(id="n0", kind="expert", name="需求分析"),
            DAGNode(id="n0", kind="skill", name="smoke-test"),
        ]
        with pytest.raises(ValidationError):
            RoutingDecision(
                dag=nodes,
                rationale="broken",
                confidence=0.5,
                detected_target_type="other",
            )

    def test_decision_confidence_bounds(self):
        """confidence must be 0.0-1.0."""
        from pydantic import ValidationError

        from runtime.router.schema import DAGNode, RoutingDecision
        node = DAGNode(id="n0", kind="expert", name="test")
        with pytest.raises(ValidationError):
            RoutingDecision(dag=[node], rationale="x", confidence=1.5, detected_target_type="other")

    def test_topological_linear(self):
        """topological() should return nodes in order for a linear DAG."""
        from runtime.router.schema import DAGNode, RoutingDecision
        nodes = [
            DAGNode(id="n0", kind="expert", name="first"),
            DAGNode(id="n1", kind="skill", name="second", depends_on=["n0"]),
            DAGNode(id="n2", kind="skill", name="third", depends_on=["n1"]),
        ]
        dec = RoutingDecision(
            dag=nodes, rationale="linear", confidence=0.9, detected_target_type="other"
        )
        ordered = dec.topological()
        assert [n.id for n in ordered] == ["n0", "n1", "n2"]

    def test_topological_diamond(self):
        """topological() should handle diamond-shaped DAG."""
        from runtime.router.schema import DAGNode, RoutingDecision
        nodes = [
            DAGNode(id="n0", kind="expert", name="start"),
            DAGNode(id="n1", kind="skill", name="left", depends_on=["n0"]),
            DAGNode(id="n2", kind="skill", name="right", depends_on=["n0"]),
            DAGNode(id="n3", kind="skill", name="end", depends_on=["n1", "n2"]),
        ]
        dec = RoutingDecision(
            dag=nodes, rationale="diamond", confidence=0.9, detected_target_type="other"
        )
        ordered = dec.topological()
        assert ordered[0].id == "n0"
        assert ordered[-1].id == "n3"
        assert set(n.id for n in ordered[1:3]) == {"n1", "n2"}

    def test_topological_cycle_raises(self):
        """topological() should raise on cyclic DAG."""
        from runtime.router.schema import DAGNode, RoutingDecision
        nodes = [
            DAGNode(id="n0", kind="expert", name="a", depends_on=["n1"]),
            DAGNode(id="n1", kind="skill", name="b", depends_on=["n0"]),
        ]
        dec = RoutingDecision(
            dag=nodes, rationale="cycle", confidence=0.9, detected_target_type="other"
        )
        with pytest.raises(ValueError, match="cycles"):
            dec.topological()

    def test_topological_unknown_dep_raises(self):
        """topological() should raise on reference to non-existent node."""
        from runtime.router.schema import DAGNode, RoutingDecision
        nodes = [
            DAGNode(id="n0", kind="expert", name="a", depends_on=["n_missing"]),
        ]
        dec = RoutingDecision(
            dag=nodes, rationale="bad ref", confidence=0.9, detected_target_type="other"
        )
        with pytest.raises(ValueError, match="unknown dep"):
            dec.topological()

    def test_decision_defaults(self):
        """RoutingDecision defaults should be sensible."""
        from runtime.router.schema import DAGNode, RoutingDecision
        nodes = [DAGNode(id="n0", kind="expert", name="test")]
        dec = RoutingDecision(
            dag=nodes, rationale="x", confidence=0.5, detected_target_type="other"
        )
        assert dec.detected_qualities == []
        assert dec.missing_inputs == []


class TestTargetArtifact:
    def test_artifact_text_kind(self):
        """TargetArtifact for text input."""
        from runtime.router.schema import TargetArtifact
        art = TargetArtifact(kind="text", text="hello world")
        assert art.kind == "text"
        assert art.text == "hello world"

    def test_artifact_file_kind(self):
        """TargetArtifact for file input."""
        from runtime.router.schema import TargetArtifact
        art = TargetArtifact(
            kind="file", path="/tmp/test.md", text="# Hello", mime="text/plain", size_bytes=1024
        )
        assert art.mime == "text/plain"
        assert art.size_bytes == 1024

    def test_artifact_url_kind(self):
        """TargetArtifact for URL input."""
        from runtime.router.schema import TargetArtifact
        art = TargetArtifact(kind="url", text="https://example.com")
        assert art.extra == {}

    def test_artifact_extra_dict(self):
        """TargetArtifact extra field should accept arbitrary dict."""
        from runtime.router.schema import TargetArtifact
        art = TargetArtifact(
            kind="file", extra={"category": "mobile-app", "version": "2.0"}
        )
        assert art.extra["category"] == "mobile-app"


# ═══════════════════════════════════════════════════════════════════════════
# llm_cache.py — cache key generation, get/set, stats, clear
# ═══════════════════════════════════════════════════════════════════════════

class TestLLMCache:
    def test_cache_key_deterministic(self):
        """Same inputs should produce same cache key."""
        from runtime.router.llm_cache import _cache_key
        k1 = _cache_key("claude", "sonnet", "sys", "user", 0.7)
        k2 = _cache_key("claude", "sonnet", "sys", "user", 0.7)
        assert k1 == k2
        assert len(k1) == 32  # hex digest truncated to 32

    def test_cache_key_different_providers(self):
        """Different providers should produce different keys."""
        from runtime.router.llm_cache import _cache_key
        k1 = _cache_key("claude", "m", "s", "u", 0.0)
        k2 = _cache_key("openai", "m", "s", "u", 0.0)
        assert k1 != k2

    def test_cache_key_different_temperature(self):
        """Slightly different temperature should produce different keys."""
        from runtime.router.llm_cache import _cache_key
        k1 = _cache_key("c", "m", "s", "u", 0.70)
        k2 = _cache_key("c", "m", "s", "u", 0.71)
        assert k1 != k2

    def test_cache_set_and_get(self, tmp_path, monkeypatch):
        """set_cached + get_cached round trip."""
        from runtime.router import llm_cache
        monkeypatch.setattr(llm_cache, "_cache_dir", lambda: tmp_path)
        monkeypatch.setattr(llm_cache, "_ttl", lambda: 99999)

        llm_cache.set_cached("claude", "sonnet", "system prompt", "user text", 0.5, "response!")
        result = llm_cache.get_cached("claude", "sonnet", "system prompt", "user text", 0.5)
        assert result == "response!"

    def test_cache_expired(self, tmp_path, monkeypatch):
        """Expired cache entry should return None."""
        from runtime.router import llm_cache
        monkeypatch.setattr(llm_cache, "_cache_dir", lambda: tmp_path)
        monkeypatch.setattr(llm_cache, "_ttl", lambda: -1)  # always expired

        llm_cache.set_cached("c", "m", "s", "u", 0.0, "old")
        result = llm_cache.get_cached("c", "m", "s", "u", 0.0)
        assert result is None

    def test_cache_miss(self, tmp_path, monkeypatch):
        """Non-existent cache entry should return None."""
        from runtime.router import llm_cache
        monkeypatch.setattr(llm_cache, "_cache_dir", lambda: tmp_path)
        result = llm_cache.get_cached("c", "m", "s", "u", 0.0)
        assert result is None

    def test_cache_stats(self, tmp_path, monkeypatch):
        """cache_stats should report entry count and size."""
        from runtime.router import llm_cache
        monkeypatch.setattr(llm_cache, "_cache_dir", lambda: tmp_path)
        llm_cache.set_cached("c", "m", "sys", "user", 0.0, "hello")
        stats = llm_cache.cache_stats()
        assert stats["entries"] == 1
        assert stats["size_kb"] >= 0
        assert stats["ttl_hours"] >= 0

    def test_clear_cache(self, tmp_path, monkeypatch):
        """clear_cache should remove all entries."""
        from runtime.router import llm_cache
        monkeypatch.setattr(llm_cache, "_cache_dir", lambda: tmp_path)
        llm_cache.set_cached("c", "m", "s", "u", 0.0, "a")
        llm_cache.set_cached("c", "m2", "s", "u", 0.0, "b")
        assert llm_cache.cache_stats()["entries"] == 2
        removed = llm_cache.clear_cache()
        assert removed == 2
        assert llm_cache.cache_stats()["entries"] == 0

    def test_set_cache_overwrites(self, tmp_path, monkeypatch):
        """Setting same key twice should overwrite."""
        from runtime.router import llm_cache
        monkeypatch.setattr(llm_cache, "_cache_dir", lambda: tmp_path)
        monkeypatch.setattr(llm_cache, "_ttl", lambda: 99999)
        llm_cache.set_cached("c", "m", "s", "u", 0.0, "v1")
        llm_cache.set_cached("c", "m", "s", "u", 0.0, "v2")
        assert llm_cache.get_cached("c", "m", "s", "u", 0.0) == "v2"


# ═══════════════════════════════════════════════════════════════════════════
# model_router.py — model tier selection, task classification, provider mapping
# ═══════════════════════════════════════════════════════════════════════════

class TestModelRouter:
    def test_get_current_provider_default(self, monkeypatch):
        """Default provider should be claude."""
        monkeypatch.delenv("TAGENT_LLM_PROVIDER", raising=False)
        from runtime.router.model_router import get_current_provider
        assert get_current_provider() == "claude"

    def test_get_current_provider_env(self, monkeypatch):
        """Provider should be read from env."""
        monkeypatch.setenv("TAGENT_LLM_PROVIDER", "deepseek")
        from runtime.router.model_router import get_current_provider
        assert get_current_provider() == "deepseek"

    def test_get_model_tier_claude(self, monkeypatch):
        """Claude tier should map haiku/sonnet with anthropic prefix."""
        monkeypatch.setenv("TAGENT_LLM_PROVIDER", "claude")
        monkeypatch.delenv("TAGENT_LLM_MODEL", raising=False)
        monkeypatch.delenv("TAGENT_LLM_HEAVY_MODEL", raising=False)
        from runtime.router.model_router import get_model_tier
        tier = get_model_tier()
        assert tier.provider == "claude"
        assert "haiku" in tier.light_model
        assert "sonnet" in tier.heavy_model

    def test_get_model_tier_deepseek(self, monkeypatch):
        """DeepSeek tier should use deepseek prefix."""
        monkeypatch.setenv("TAGENT_LLM_PROVIDER", "deepseek")
        monkeypatch.delenv("TAGENT_LLM_MODEL", raising=False)
        from runtime.router.model_router import get_model_tier
        tier = get_model_tier()
        assert "deepseek" in tier.light_model
        assert "deepseek" in tier.heavy_model

    def test_get_model_tier_ollama_no_prefix(self, monkeypatch):
        """Ollama models should not have provider prefix."""
        monkeypatch.setenv("TAGENT_LLM_PROVIDER", "ollama")
        monkeypatch.delenv("TAGENT_LLM_MODEL", raising=False)
        from runtime.router.model_router import get_model_tier
        tier = get_model_tier()
        assert not tier.light_model.startswith("ollama/")

    def test_get_model_tier_user_override(self, monkeypatch):
        """User-specified model via TAGENT_LLM_MODEL should take precedence."""
        monkeypatch.setenv("TAGENT_LLM_PROVIDER", "claude")
        monkeypatch.setenv("TAGENT_LLM_MODEL", "claude-opus-4-8")
        from runtime.router.model_router import get_model_tier
        tier = get_model_tier()
        assert "opus" in tier.light_model

    def test_get_model_tier_heavy_override(self, monkeypatch):
        """TAGENT_LLM_HEAVY_MODEL should override heavy model."""
        monkeypatch.setenv("TAGENT_LLM_PROVIDER", "claude")
        monkeypatch.setenv("TAGENT_LLM_MODEL", "claude-haiku-4-5")
        monkeypatch.setenv("TAGENT_LLM_HEAVY_MODEL", "claude-opus-4-8")
        from runtime.router.model_router import get_model_tier
        tier = get_model_tier()
        assert "haiku" in tier.light_model
        assert "opus" in tier.heavy_model

    def test_get_model_tier_unknown_provider_passthrough(self, monkeypatch):
        """Unknown provider should pass through as-is."""
        monkeypatch.setenv("TAGENT_LLM_PROVIDER", "my-custom-provider")
        monkeypatch.delenv("TAGENT_LLM_MODEL", raising=False)
        from runtime.router.model_router import get_model_tier
        tier = get_model_tier()
        assert tier.provider == "my-custom-provider"
        assert tier.light_model == "my-custom-provider"

    def test_classify_task_light(self):
        """Simple routing prompt should classify as LIGHT."""
        from runtime.router.model_router import TaskTier, classify_task
        assert classify_task("route this to smoke test") == TaskTier.LIGHT
        assert classify_task("show me the catalog") == TaskTier.LIGHT
        assert classify_task("what is the status?") == TaskTier.LIGHT

    def test_classify_task_heavy(self):
        """Test execution prompts should classify as HEAVY."""
        from runtime.router.model_router import TaskTier, classify_task
        assert classify_task("execute all tests for this system") == TaskTier.HEAVY
        assert classify_task("generate a full penetration test report") == TaskTier.HEAVY
        assert classify_task("analyze security vulnerabilities") == TaskTier.HEAVY

    def test_classify_task_long_prompt_heavy(self):
        """Long prompts (>200 chars) without keywords default to HEAVY."""
        from runtime.router.model_router import TaskTier, classify_task
        long_prompt = "x" * 250
        assert classify_task(long_prompt) == TaskTier.HEAVY

    def test_classify_task_short_prompt_light(self):
        """Short prompts without keywords default to LIGHT."""
        from runtime.router.model_router import TaskTier, classify_task
        assert classify_task("hello") == TaskTier.LIGHT

    def test_classify_task_chinese(self):
        """Chinese keywords should be detected."""
        from runtime.router.model_router import TaskTier, classify_task
        assert classify_task("执行冒烟测试") == TaskTier.HEAVY
        assert classify_task("列出所有技能") == TaskTier.LIGHT

    def test_select_model_light_task(self, monkeypatch):
        """select_model for light task should return light model."""
        monkeypatch.setenv("TAGENT_LLM_PROVIDER", "deepseek")
        monkeypatch.delenv("TAGENT_LLM_MODEL", raising=False)
        from runtime.router.model_router import select_model
        model = select_model("show me the catalog")
        assert "chat" in model  # deepseek-chat (light)

    def test_select_model_heavy_task(self, monkeypatch):
        """select_model for heavy task should return heavy model."""
        monkeypatch.setenv("TAGENT_LLM_PROVIDER", "deepseek")
        monkeypatch.delenv("TAGENT_LLM_MODEL", raising=False)
        from runtime.router.model_router import select_model
        model = select_model("execute all penetration tests")
        assert "reasoner" in model  # deepseek-reasoner (heavy)

    def test_task_tier_enum(self):
        """TaskTier enum should have LIGHT and HEAVY."""
        from runtime.router.model_router import TaskTier
        assert TaskTier.LIGHT is not None
        assert TaskTier.HEAVY is not None
        assert TaskTier.LIGHT != TaskTier.HEAVY

    def test_prefixed_already_qualified(self):
        """_prefixed should not double-prefix already qualified names."""
        from runtime.router.model_router import _prefixed
        result = _prefixed("claude", "anthropic/claude-sonnet-4-6")
        assert result == "anthropic/claude-sonnet-4-6"

    def test_prefixed_stub_passthrough(self):
        """_prefixed should pass through stub models."""
        from runtime.router.model_router import _prefixed
        assert _prefixed("stub", "stub") == "stub"

    def test_all_default_providers_have_models(self, monkeypatch):
        """Every provider in _DEFAULT_MODELS should resolve without error."""
        monkeypatch.delenv("TAGENT_LLM_MODEL", raising=False)
        from runtime.router.model_router import _DEFAULT_MODELS, get_model_tier
        for provider in _DEFAULT_MODELS:
            monkeypatch.setenv("TAGENT_LLM_PROVIDER", provider)
            tier = get_model_tier()
            assert tier.light_model, f"{provider} missing light model"
            assert tier.heavy_model, f"{provider} missing heavy model"


# ═══════════════════════════════════════════════════════════════════════════
# prompt.py — system prompt + user prompt builder
# ═══════════════════════════════════════════════════════════════════════════

class TestPrompt:
    def test_system_prompt_exists(self):
        """SYSTEM_PROMPT should be a non-empty string."""
        from runtime.router.prompt import SYSTEM_PROMPT
        assert len(SYSTEM_PROMPT) > 500
        assert "ROUTING" in SYSTEM_PROMPT.upper() or "routing" in SYSTEM_PROMPT.lower()

    def test_system_prompt_has_schema(self):
        """SYSTEM_PROMPT should mention JSON schema fields."""
        from runtime.router.prompt import SYSTEM_PROMPT
        assert '"dag"' in SYSTEM_PROMPT
        assert '"confidence"' in SYSTEM_PROMPT

    def test_system_prompt_has_rules(self):
        """SYSTEM_PROMPT should contain HARD RULES."""
        from runtime.router.prompt import SYSTEM_PROMPT
        assert "HARD RULES" in SYSTEM_PROMPT

    def test_build_user_prompt_has_catalog(self, monkeypatch):
        """build_user_prompt should include expert and skill names."""
        from runtime.router.prompt import build_user_prompt
        from runtime.router.schema import TargetArtifact

        # Minimal mock catalog
        class FakeExpert:
            def __init__(self, name, description):
                self.name = name
                self.description = description

        class FakeCatalog:
            def __init__(self):
                self.experts = {"e1": FakeExpert("测试主管", "test lead")}
                self.skills = {"s1": FakeExpert("smoke-test", "smoke testing")}

        artifact = TargetArtifact(kind="text", text="run tests")
        result = build_user_prompt(artifact, FakeCatalog())  # type: ignore[arg-type]
        assert "测试主管" in result
        assert "smoke-test" in result
        assert "run tests" in result
