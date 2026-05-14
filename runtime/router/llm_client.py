"""LiteLLM multi-provider wrapper + local Ollama fallback + stub for tests."""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from runtime.config.settings import get_settings

PROVIDER_MODEL_MAP: dict[str, str] = {
    "claude": "anthropic/claude-sonnet-4-6",
    "openai": "openai/gpt-4o",
    "gemini": "gemini/gemini-1.5-pro",
    "qwen": "dashscope/qwen-plus",
    "deepseek": "deepseek/deepseek-chat",
    "ollama": "ollama/qwen2.5:7b",
}


class LLMError(RuntimeError):
    pass


class LLMClient:
    """Thin wrapper. Real call via litellm.completion; stub provider returns canned JSON."""

    def __init__(self, provider: str | None = None, fallback: str | None = None) -> None:
        s = get_settings()
        self.provider = provider or s.llm_provider
        self.fallback = fallback or s.llm_provider_fallback
        self.timeout = s.llm_timeout_seconds
        self.max_retries = s.llm_max_retries

    def complete_json(self, system: str, user: str, *, temperature: float = 0.1) -> dict[str, Any]:
        """Return parsed JSON object. Tries primary provider then fallback."""
        for prov in [self.provider, self.fallback]:
            try:
                raw = self._call(prov, system, user, temperature)
                return self._extract_json(raw)
            except Exception as e:  # noqa: BLE001
                logger.warning("provider {} failed: {}", prov, e)
        raise LLMError(f"all providers failed: primary={self.provider} fallback={self.fallback}")

    def complete(self, system: str, user: str, *, temperature: float = 0.1, max_tokens: int = 256) -> str:
        """Plain text completion(no JSON parse)· healthcheck probe / 简单总结 用."""
        for prov in [self.provider, self.fallback]:
            try:
                return self._call(prov, system, user, temperature, max_tokens=max_tokens, json_mode=False)
            except Exception as e:  # noqa: BLE001
                logger.warning("provider {} failed: {}", prov, e)
        raise LLMError(f"all providers failed: primary={self.provider} fallback={self.fallback}")

    def _call(self, provider: str, system: str, user: str, temperature: float, *, max_tokens: int | None = None, json_mode: bool = True) -> str:
        if provider == "stub":
            return _stub_response(system, user) if json_mode else "stub: ok"
        try:
            import litellm  # local import keeps tests cheap
        except ImportError as e:
            raise LLMError("litellm not installed; pip install litellm") from e

        model = PROVIDER_MODEL_MAP.get(provider, provider)
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "timeout": self.timeout,
            "num_retries": self.max_retries,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        resp = litellm.completion(**kwargs)
        return resp["choices"][0]["message"]["content"]

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            # strip leading lang tag e.g. ```json
            if "\n" in raw:
                _, raw = raw.split("\n", 1)
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < 0:
            raise LLMError(f"no JSON object in response: {raw[:200]}")
        return json.loads(raw[start : end + 1])


def _stub_response(_system: str, user: str) -> str:
    """Deterministic stub for tests. Picks plausible experts/skills from keywords.

    Only scans the TARGET ARTIFACT section, NOT the catalog (which contains all keywords).
    """
    marker = "TARGET ARTIFACT:"
    idx = user.find(marker)
    target_text = user[idx + len(marker) :].lower() if idx >= 0 else user.lower()
    # Order matters: most-specific first to avoid 'api' inside 'mobile-application' style overlap.
    # 全 5 path 末统一 test-lead 决策(主宪章 §40 + 02-专家定义/README.md 流程
    # "bug-manager → report-generator → test-lead 决策")
    if any(k in target_text for k in ("apk", "ipa", " android", "\"android", " ios", "\"ios", "mobile-app", " mobile ")):
        target = "mobile-app"
        experts = ["requirements-analyst", "testcase-designer", "mobile-tester", "test-executor", "bug-manager", "report-generator", "test-lead"]
    elif any(k in target_text for k in (".exe", " exe ", "desktop", "windows", ".msi", ".dmg")):
        target = "desktop-app"
        experts = ["requirements-analyst", "testcase-designer", "desktop-tester", "test-executor", "bug-manager", "report-generator", "test-lead"]
    elif any(k in target_text for k in ("llm ", " llm", "ai model", "ai-model", "ml model", "model evaluation", "embedding")):
        target = "ai-model"
        experts = ["requirements-analyst", "testcase-designer", "ai-tester", "test-executor", "bug-manager", "report-generator", "test-lead"]
    elif any(k in target_text for k in ("rest api", "rest-api", "grpc", "graphql", " api ", "\"api", "endpoint", "openapi", "swagger")):
        target = "rest-api"
        experts = ["requirements-analyst", "testcase-designer", "automation-engineer", "test-executor", "bug-manager", "report-generator", "test-lead"]
    else:
        target = "web-system"
        experts = [
            "requirements-analyst",
            "testcase-designer",
            "env-manager",
            "data-preparer",
            "automation-engineer",
            "test-executor",
            "bug-manager",
            "report-generator",
            "test-lead",
        ]
    nodes = []
    prev = None
    for i, exp in enumerate(experts):
        node = {
            "id": f"n{i}",
            "kind": "expert",
            "name": exp,
            "depends_on": [prev] if prev else [],
            "inputs": {},
            "on_failure": "retry",
            "timeout_seconds": 1800,
        }
        nodes.append(node)
        prev = node["id"]
    return json.dumps(
        {
            "dag": nodes,
            "rationale": "stub: linear default flow",
            "confidence": 0.7,
            "detected_target_type": target,
            "detected_qualities": ["functional", "regression"],
            "missing_inputs": [],
        },
        ensure_ascii=False,
    )
