"""Model auto-routing: select the right model tier based on task complexity.

Light tasks (classification, routing, simple queries) use fast/cheap models.
Heavy tasks (test execution, analysis, generation) use powerful models.

Supports ANY LiteLLM-compatible provider — official, proxy (中转站), third-party, local.
No provider whitelist. Set TAGENT_LLM_PROVIDER + API key, done.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum, auto


class TaskTier(Enum):
    LIGHT = auto()   # classification, routing — cheap/fast model
    HEAVY = auto()   # execution, generation — powerful model


@dataclass
class ModelTier:
    provider: str
    light_model: str    # fast/cheap for routing & classification
    heavy_model: str    # powerful for test execution
    api_base: str | None = None  # relay/proxy endpoint


# ── Convenience defaults for well-known providers ────────────────────
# These are FALLBACKS — any provider works.
# Unknown providers require TAGENT_LLM_MODEL in .env.

# LiteLLM provider → (light_model, heavy_model)
# Model names are bare — _prefixed() adds the correct LiteLLM prefix.
_DEFAULT_MODELS: dict[str, tuple[str, str]] = {
    "claude":    ("claude-haiku-4-5",       "claude-sonnet-4-6"),
    "openai":    ("gpt-4o-mini",            "gpt-4o"),
    "gemini":    ("gemini-2.5-flash",       "gemini-2.5-pro"),
    "deepseek":  ("deepseek-chat",          "deepseek-reasoner"),
    "qwen":      ("qwen-turbo",             "qwen-plus"),
    "zhipu":     ("glm-4-flash",            "glm-4-plus"),
    "ollama":    ("qwen2.5:7b",             "qwen2.5:7b"),
    "stub":      ("stub",                   "stub"),
}

# Map user-facing provider name → LiteLLM provider prefix
# LiteLLM expects {prefix}/{model}, e.g. "anthropic/claude-sonnet-4-6"
_LITELLM_PREFIX: dict[str, str] = {
    "claude":    "anthropic",
    "anthropic": "anthropic",
    "deepseek":  "deepseek",
    "openai":    "openai",
    "gemini":    "gemini",
    "qwen":      "dashscope",
    "zhipu":     "zhipu",
    "ollama":    "ollama",
}


def _prefixed(provider: str, model: str) -> str:
    """Auto-prefix model with correct LiteLLM provider prefix.

    E.g. provider='claude', model='claude-sonnet-4-6'
      → 'anthropic/claude-sonnet-4-6'
    """
    if "/" in model:
        return model  # already fully qualified
    if provider in ("stub",):
        return model
    prefix = _LITELLM_PREFIX.get(provider, provider)
    if provider == "ollama":
        return model  # ollama models don't need prefix
    return f"{prefix}/{model}"


def get_current_provider() -> str:
    return os.environ.get("TAGENT_LLM_PROVIDER", "claude")


def get_model_tier(provider: str | None = None) -> ModelTier:
    """Return model tier for provider. Supports any LiteLLM provider.

    Resolution order:
    1. TAGENT_LLM_MODEL / TAGENT_LLM_HEAVY_MODEL → override everything
    2. Provider defaults (convenience fallback)
    3. Provider name as-is (passthrough for unknown providers)
    """
    provider = provider or get_current_provider()
    api_base = os.environ.get("TAGENT_LLM_API_BASE") or None

    # ── User override: explicit model names ──
    user_model = os.environ.get("TAGENT_LLM_MODEL", "")
    user_heavy = os.environ.get("TAGENT_LLM_HEAVY_MODEL", "") or user_model

    if user_model:
        light = _prefixed(provider, user_model)
        heavy = _prefixed(provider, user_heavy)
    elif provider in _DEFAULT_MODELS:
        light_model, heavy_model = _DEFAULT_MODELS[provider]
        light = _prefixed(provider, light_model)
        heavy = _prefixed(provider, heavy_model)
    else:
        # Unknown provider — pass through as-is, LiteLLM will try its best
        light = provider
        heavy = provider

    return ModelTier(
        provider=provider,
        light_model=light,
        heavy_model=heavy,
        api_base=api_base,
    )


def classify_task(prompt: str) -> TaskTier:
    """Classify task as LIGHT or HEAVY based on prompt characteristics.

    LIGHT: routing, classification, simple queries, catalog, status
    HEAVY: test execution, analysis, report generation, penetration testing
    """
    text = prompt.lower()
    length = len(prompt)

    light_keywords = [
        "route", "classify", "catalog", "status", "list", "help",
        "what is", "show me", "explain", "summarize",
        "路由", "分类", "列出", "状态", "帮助", "是什么",
    ]

    heavy_keywords = [
        "test", "execute", "generate", "analyze", "scan", "report",
        "penetration", "pentest", "fuzz", "performance", "load test",
        "测试", "执行", "生成", "分析", "扫描", "报告", "渗透",
        "回归测试", "性能测试", "安全测试",
    ]

    heavy_score = sum(1 for kw in heavy_keywords if kw in text)
    light_score = sum(1 for kw in light_keywords if kw in text)

    if heavy_score > light_score:
        return TaskTier.HEAVY
    if light_score > heavy_score:
        return TaskTier.LIGHT

    return TaskTier.HEAVY if length > 200 else TaskTier.LIGHT


def select_model(prompt: str, provider: str | None = None) -> str:
    """Select the appropriate model for a given prompt and provider.

    Returns the LiteLLM model string (e.g. 'deepseek/deepseek-chat').
    Supports relay/proxy via TAGENT_LLM_API_BASE.
    """
    tier = get_model_tier(provider)
    task = classify_task(prompt)
    return tier.heavy_model if task == TaskTier.HEAVY else tier.light_model
