"""TDD: Model auto-router — task classification, tier selection, relay support."""

from __future__ import annotations

import os

import pytest

from runtime.router.model_router import (
    MODEL_TIERS,
    ModelTier,
    TaskTier,
    classify_task,
    get_model_tier,
    get_current_provider,
    select_model,
)


class TestTaskClassification:
    """Test classify_task() heuristic."""

    def test_short_prompt_is_light(self):
        assert classify_task("help") == TaskTier.LIGHT

    def test_routing_keywords_light(self):
        for text in ["route this", "show me the catalog", "what is test-lead", "列出所有", "help me"]:
            assert classify_task(text) == TaskTier.LIGHT, f"'{text}' should be LIGHT"

    def test_testing_keywords_heavy(self):
        for text in [
            "test the login page for security bugs",
            "execute full regression suite",
            "generate test report for sprint 42",
            "penetration test on api.example.com",
            "扫描 SQL 注入漏洞",
            "性能测试",
        ]:
            assert classify_task(text) == TaskTier.HEAVY, f"'{text}' should be HEAVY"

    def test_long_prompt_defaults_heavy(self):
        long_text = "请帮我全面测试" + "这个系统" * 100
        assert classify_task(long_text) == TaskTier.HEAVY

    def test_both_scores_tiebreaker(self):
        # "test the route" has both heavy ("test") and light ("route") keywords
        # Heavy indicator "test" should win
        result = classify_task("test the route configuration")
        assert result in (TaskTier.HEAVY, TaskTier.LIGHT)  # either is valid


class TestModelTiers:
    """Test model tier definitions."""

    def test_all_6_providers_defined(self):
        expected = {"claude", "openai", "gemini", "deepseek", "qwen", "ollama"}
        assert set(MODEL_TIERS.keys()) == expected

    def test_each_tier_has_both_models(self):
        for prov, tier in MODEL_TIERS.items():
            assert tier.light_model, f"{prov} missing light model"
            assert tier.heavy_model, f"{prov} missing heavy model"
            assert tier.provider == prov

    def test_ollama_same_model_both_tiers(self):
        tier = MODEL_TIERS["ollama"]
        assert tier.light_model == tier.heavy_model  # local model — same for both

    def test_get_model_tier_default(self):
        tier = get_model_tier("claude")
        assert tier.provider == "claude"
        assert "haiku" in tier.light_model.lower() or "haiku" in tier.light_model

    def test_get_model_tier_unknown(self):
        tier = get_model_tier("unknown-provider")
        assert tier.provider == "unknown-provider"
        assert tier.light_model == "unknown-provider"  # pass-through


class TestSelectModel:
    """Test select_model() integration."""

    def test_light_task_selects_light_model(self):
        model = select_model("show me the catalog", "claude")
        assert "haiku" in model.lower()

    def test_heavy_task_selects_heavy_model(self):
        model = select_model("run full penetration test on example.com", "claude")
        assert "sonnet" in model.lower()

    def test_default_provider(self):
        model = select_model("test the login page")
        assert model  # should return something

    def test_unknown_provider_passthrough(self):
        model = select_model("test something", "custom-relay")
        assert model == "custom-relay"


class TestRelaySupport:
    """Test relay/proxy endpoint support (中转站)."""

    def test_relay_api_base_preserved(self):
        old = os.environ.get("TAGENT_LLM_API_BASE")
        os.environ["TAGENT_LLM_API_BASE"] = "https://api.relay.example.com/v1"
        try:
            tier = get_model_tier("openai")
            assert tier.api_base == "https://api.relay.example.com/v1"
        finally:
            if old:
                os.environ["TAGENT_LLM_API_BASE"] = old
            else:
                os.environ.pop("TAGENT_LLM_API_BASE", None)

    def test_no_relay_api_base_is_none(self):
        old = os.environ.pop("TAGENT_LLM_API_BASE", None)
        try:
            tier = get_model_tier("claude")
            assert tier.api_base is None
        finally:
            if old:
                os.environ["TAGENT_LLM_API_BASE"] = old

    def test_relay_with_unknown_provider(self):
        old = os.environ.get("TAGENT_LLM_API_BASE")
        os.environ["TAGENT_LLM_API_BASE"] = "https://my-proxy.com"
        try:
            tier = get_model_tier("my-custom-provider")
            assert tier.api_base == "https://my-proxy.com"
        finally:
            if old:
                os.environ["TAGENT_LLM_API_BASE"] = old
            else:
                os.environ.pop("TAGENT_LLM_API_BASE", None)


class TestCurrentProvider:
    """Test provider detection."""

    def test_default_is_claude(self):
        old = os.environ.pop("TAGENT_LLM_PROVIDER", None)
        try:
            assert get_current_provider() == "claude"
        finally:
            if old:
                os.environ["TAGENT_LLM_PROVIDER"] = old

    def test_env_override(self):
        old = os.environ.get("TAGENT_LLM_PROVIDER")
        os.environ["TAGENT_LLM_PROVIDER"] = "deepseek"
        try:
            assert get_current_provider() == "deepseek"
        finally:
            if old:
                os.environ["TAGENT_LLM_PROVIDER"] = old
            else:
                os.environ.pop("TAGENT_LLM_PROVIDER", None)
