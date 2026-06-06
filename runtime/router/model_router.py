"""Model auto-routing: select the right model tier based on task complexity.

Light tasks (classification, routing, simple queries) use fast/cheap models.
Heavy tasks (test execution, analysis, generation) use powerful models.

Supports relay/proxy API endpoints (中转站) via TAGENT_LLM_API_BASE.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TaskTier(Enum):
    LIGHT = auto()   # classification, routing — cheap/fast model
    HEAVY = auto()   # execution, generation — powerful model


@dataclass
class ModelTier:
    provider: str
    light_model: str    # fast/cheap for routing & classification
    heavy_model: str    # powerful for test execution
    api_base: str | None = None  # relay/proxy endpoint


# ── model tiers per provider ────────────────────────────────────────

MODEL_TIERS: dict[str, ModelTier] = {
    "claude": ModelTier("claude",
        light_model="anthropic/claude-haiku-4-5",
        heavy_model="anthropic/claude-sonnet-4-6",
    ),
    "openai": ModelTier("openai",
        light_model="openai/gpt-4o-mini",
        heavy_model="openai/gpt-4o",
    ),
    "gemini": ModelTier("gemini",
        light_model="gemini/gemini-2.5-flash",
        heavy_model="gemini/gemini-1.5-pro",
    ),
    "deepseek": ModelTier("deepseek",
        light_model="deepseek/deepseek-chat",
        heavy_model="deepseek/deepseek-reasoner",
    ),
    "qwen": ModelTier("qwen",
        light_model="dashscope/qwen-turbo",
        heavy_model="dashscope/qwen-plus",
    ),
    "ollama": ModelTier("ollama",
        light_model="ollama/qwen2.5:7b",
        heavy_model="ollama/qwen2.5:7b",
    ),
}


def get_current_provider() -> str:
    return os.environ.get("TAGENT_LLM_PROVIDER", "claude")


def get_model_tier(provider: str | None = None) -> ModelTier:
    """Return model tier for provider, with relay/proxy override."""
    provider = provider or get_current_provider()

    # Check for relay/proxy endpoint override
    api_base = os.environ.get("TAGENT_LLM_API_BASE") or None

    # Default tier for unknown providers — use as-is with fallback
    if provider not in MODEL_TIERS:
        return ModelTier(
            provider=provider,
            light_model=provider,   # pass through as-is
            heavy_model=provider,
            api_base=api_base,
        )

    tier = MODEL_TIERS[provider]
    if api_base:
        tier = ModelTier(
            provider=tier.provider,
            light_model=tier.light_model,
            heavy_model=tier.heavy_model,
            api_base=api_base,
        )
    return tier


def classify_task(prompt: str) -> TaskTier:
    """Classify task as LIGHT or HEAVY based on prompt characteristics.

    LIGHT: routing, classification, simple queries, catalog, status
    HEAVY: test execution, analysis, report generation, penetration testing
    """
    text = prompt.lower()
    length = len(prompt)

    # Light indicators: short routing/classification queries
    light_keywords = [
        "route", "classify", "catalog", "status", "list", "help",
        "what is", "show me", "explain", "summarize",
        "路由", "分类", "列出", "状态", "帮助", "是什么",
    ]

    # Heavy indicators: execution, analysis, generation
    heavy_keywords = [
        "test", "execute", "generate", "analyze", "scan", "report",
        "penetration", "pentest", "fuzz", "performance", "load test",
        "测试", "执行", "生成", "分析", "扫描", "报告", "渗透",
        "回归测试", "性能测试", "安全测试",
    ]

    # Check heavy indicators first (more specific)
    heavy_score = sum(1 for kw in heavy_keywords if kw in text)
    light_score = sum(1 for kw in light_keywords if kw in text)

    if heavy_score > light_score:
        return TaskTier.HEAVY
    if light_score > heavy_score:
        return TaskTier.LIGHT

    # Default: longer prompts → heavy, short without keywords → light
    return TaskTier.HEAVY if length > 200 else TaskTier.LIGHT


def select_model(prompt: str, provider: str | None = None) -> str:
    """Select the appropriate model for a given prompt and provider.

    Returns the LiteLLM model string (e.g. 'anthropic/claude-sonnet-4-6').

    Supports relay/proxy via TAGENT_LLM_API_BASE environment variable.
    """
    tier = get_model_tier(provider)
    task = classify_task(prompt)

    model = tier.heavy_model if task == TaskTier.HEAVY else tier.light_model
    return model
