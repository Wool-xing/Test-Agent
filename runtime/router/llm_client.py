"""LiteLLM multi-provider wrapper + local Ollama fallback + stub for tests."""

from __future__ import annotations

import json
import os
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

        # Auto-route model based on task complexity (P2 #14)
        try:
            from runtime.router.model_router import select_model
            model = select_model(user, provider)
        except ImportError:
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
        # 通用 OpenAI 兼容端点支持: TAGENT_LLM_API_BASE + TAGENT_LLM_API_KEY (任厂商即插即用)
        # 厂商标准 key env (ANTHROPIC_API_KEY / OPENAI_API_KEY / DASHSCOPE_API_KEY ...) 由 litellm 自动识别, 此处不重复处理
        api_base = os.environ.get("TAGENT_LLM_API_BASE")
        if api_base:
            kwargs["api_base"] = api_base
        api_key = os.environ.get("TAGENT_LLM_API_KEY")
        if api_key:
            kwargs["api_key"] = api_key
        resp = litellm.completion(**kwargs)
        return resp["choices"][0]["message"]["content"]

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        raw = raw.strip()
        if raw.startswith("```"):
            # Strip exactly one fenced code block marker
            raw = raw[3:-3].strip() if raw.endswith("```") else raw[3:]
            # strip leading lang tag e.g. ```json
            if "\n" in raw:
                _, raw = raw.split("\n", 1)
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end < 0:
            raise LLMError(f"no JSON object in response: {raw[:200]}")
        return json.loads(raw[start : end + 1])


# Order matters: most-specific first to avoid 'api' inside 'mobile-application' style overlap.
_STUB_TARGETS: list[tuple[tuple[str, ...], str, list]] = [
    (("can-bus", "can bus", " ecu ", "adas", "v2x", " ota ", "asil", "iso 26262", "iso-26262", "automotive", "vehicle", "车载", "汽车"),
     "automotive", ["requirements-analyst", "testcase-designer", "automotive-tester", "test-executor", "bug-manager", "report-generator", "test-lead"]),
    (("pentest", "penetration test", "sql injection", " xss ", " ssrf ", "owasp", "security testing", "渗透", "渗透测试"),
     "pentest", [("pentest-coordinator", "skill"), "requirements-analyst", "testcase-designer", "pentest-tester", "test-executor", "bug-manager", "report-generator", "test-lead"]),
    (("canvas", "webgl", " ocr ", "visual regression", "screenshot diff", "视觉回归", "图像对比"),
     "visual-system", ["requirements-analyst", "testcase-designer", "visual-tester", "test-executor", "bug-manager", "report-generator", "test-lead"]),
    ((" mqtt", "kafka", "rabbitmq", "jaeger", " iot ", "embedded", "modbus", "串口", "serial port"),
     "system-integration", ["requirements-analyst", "testcase-designer", "env-manager", "system-tester", "test-executor", "bug-manager", "report-generator", "test-lead"]),
    (("apk", "ipa", " android", "\"android", " ios", "\"ios", "mobile-app", " mobile "),
     "mobile-app", ["requirements-analyst", "testcase-designer", "mobile-tester", "test-executor", "bug-manager", "report-generator", "test-lead"]),
    ((".exe", " exe ", "desktop", "windows", ".msi", ".dmg"),
     "desktop-app", ["requirements-analyst", "testcase-designer", "desktop-tester", "test-executor", "bug-manager", "report-generator", "test-lead"]),
    (("llm ", " llm", "ai model", "ai-model", "ml model", "model evaluation", "embedding"),
     "ai-model", ["requirements-analyst", "testcase-designer", "ai-tester", "test-executor", "bug-manager", "report-generator", "test-lead"]),
    (("rest api", "rest-api", "grpc", "graphql", " api ", "\"api", "endpoint", "openapi", "swagger"),
     "rest-api", ["requirements-analyst", "testcase-designer", "automation-engineer", "test-executor", "bug-manager", "report-generator", "test-lead"]),
]
_STUB_DEFAULT = ("web-system", [
    "requirements-analyst", "testcase-designer", "env-manager", "data-preparer",
    "automation-engineer", "test-executor", "bug-manager", "report-generator", "test-lead",
])


def _stub_response(_system: str, user: str) -> str:
    """Deterministic stub for tests. Picks plausible experts/skills from keywords."""
    marker = "TARGET ARTIFACT:"
    idx = user.find(marker)
    target_text = user[idx + len(marker) :].lower() if idx >= 0 else user.lower()
    target, experts = _STUB_DEFAULT
    for keywords, t, exp in _STUB_TARGETS:
        if any(k in target_text for k in keywords):
            target, experts = t, exp
            break
    nodes = []
    prev = None
    for i, exp in enumerate(experts):
        if isinstance(exp, tuple):
            exp_name, exp_kind = exp
        else:
            exp_name, exp_kind = exp, "expert"
        node = {
            "id": f"n{i}",
            "kind": exp_kind,
            "name": exp_name,
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
