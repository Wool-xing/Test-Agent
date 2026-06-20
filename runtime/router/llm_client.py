"""LiteLLM multi-provider wrapper + local Ollama fallback + stub for tests."""

from __future__ import annotations

import json
import os
from typing import Any

from loguru import logger

# Suppress litellm remote cost-map fetch noise (5s timeout in air-gapped envs)
os.environ.setdefault("LITELLM_SUPPRESS_DEBUG_INFO", "1")

from runtime.config.settings import get_settings

PROVIDER_MODEL_MAP: dict[str, str] = {
    "claude": "anthropic/claude-sonnet-4-6",
    "openai": "openai/gpt-4o",
    "gemini": "gemini/gemini-1.5-pro",
    "qwen": "dashscope/qwen-plus",
    "deepseek": "deepseek/deepseek-chat",
    "zhipu": "zhipu/glm-4-plus",
    "ollama": "ollama/qwen2.5:7b",
}


def _resolve_model(provider: str) -> str:
    """Resolve provider → model name. Env override: TAGENT_LLM_MODEL_<PROVIDER>."""
    env_key = f"TAGENT_LLM_MODEL_{provider.upper()}"
    return os.getenv(env_key, PROVIDER_MODEL_MAP.get(provider, provider))


def _strip_json_fences(raw: str) -> str:
    """Strip markdown code fences + language tag from LLM output."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw[3:-3].strip() if raw.endswith("```") else raw[3:]
        if "\n" in raw:
            _, raw = raw.split("\n", 1)
    return raw


def _call_responses_api(provider: str, model: str, system: str, user: str,
                         temperature: float, max_tokens: int | None,
                         json_mode: bool) -> str:
    """OpenAI Responses API (opt-in via TAGENT_LLM_RESPONSES_API=1).
    Uses native openai SDK. Falls back to litellm Chat Completions on failure.
    """
    try:
        import openai
    except ImportError:
        raise LLMError("openai SDK not installed; pip install openai")

    api_key = os.environ.get("TAGENT_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    api_base = os.environ.get("TAGENT_LLM_API_BASE") or "https://api.openai.com/v1"

    client = openai.OpenAI(api_key=api_key, base_url=api_base)
    try:
        input_msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        kwargs: dict[str, Any] = {"model": model, "input": input_msgs, "temperature": temperature}
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        if json_mode:
            input_msgs.append({"role": "system", "content": "Respond with valid JSON only."})

        resp = client.responses.create(**kwargs)
        return resp.output_text
    finally:
        client.close()


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

    @staticmethod
    def _resolve_model(provider: str, user: str) -> str:
        """Resolve model name: model_router if available, else provider default."""
        try:
            from runtime.router.model_router import select_model
            return select_model(user, provider)
        except ImportError:
            return _resolve_model(provider)

    @staticmethod
    def _try_cache(provider: str, model: str, system: str, user: str,
                   temperature: float) -> str | None:
        """Check LLM response cache. Returns cached result or None."""
        try:
            from runtime.router.llm_cache import get_cached
        except ImportError:
            return None
        try:
            return get_cached(provider, model, system, user, temperature)
        except Exception:
            return None

    def _call(self, provider: str, system: str, user: str, temperature: float, *,
              max_tokens: int | None = None, json_mode: bool = True) -> str:
        if provider == "stub":
            return _stub_response(system, user) if json_mode else "stub: ok"

        model = self._resolve_model(provider, user)
        if os.environ.get("TAGENT_LLM_MODEL"):
            model = os.environ["TAGENT_LLM_MODEL"]

        cached = self._try_cache(provider, model, system, user, temperature)
        if cached is not None:
            return cached

        try:
            import litellm
        except ImportError as e:
            raise LLMError("litellm not installed; pip install litellm") from e

        if os.environ.get("TAGENT_LLM_RESPONSES_API") == "1":
            try:
                return _call_responses_api(provider, model, system, user,
                                           temperature, max_tokens, json_mode)
            except Exception:
                logger.debug("Responses API failed, falling back to Chat Completions")

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
        api_base = os.environ.get("TAGENT_LLM_API_BASE")
        if api_base:
            kwargs["api_base"] = api_base
        api_key = os.environ.get("TAGENT_LLM_API_KEY")
        if api_key:
            kwargs["api_key"] = api_key

        resp = litellm.completion(**kwargs)
        result = resp["choices"][0]["message"]["content"]
        try:
            from runtime.router.llm_cache import set_cached
            if set_cached and provider != "stub":
                set_cached(provider, model, system, user, temperature, result)
        except Exception:
            pass
        return result

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        raw = _strip_json_fences(raw)
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
    _STUB_ONELINERS = {
        "requirements-analyst": "分析输入并提取测试需求",
        "testcase-designer": "根据需求设计测试用例",
        "env-manager": "准备测试环境与依赖",
        "data-preparer": "生成或加载测试数据",
        "automation-engineer": "编写自动化测试脚本",
        "automotive-tester": "执行车载系统专项测试",
        "mobile-tester": "执行移动端专项测试",
        "desktop-tester": "执行桌面端专项测试",
        "visual-tester": "执行视觉/游戏专项测试",
        "system-tester": "执行系统集成专项测试",
        "ai-tester": "执行 AI 模型专项测试",
        "pentest-tester": "执行渗透测试",
        "test-executor": "执行已生成的测试用例",
        "bug-manager": "收集并分类发现的问题",
        "report-generator": "汇总测试结果生成报告",
        "test-lead": "协调全流程并输出最终结论",
    }
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
            "one_liner_zh": _STUB_ONELINERS.get(exp_name, f"执行 {exp_name} 任务"),
            "one_liner_en": f"Execute {exp_name} task",
            "why": _STUB_ONELINERS.get(exp_name, ""),
            "theory_refs": [],
            "alternatives": [],
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
