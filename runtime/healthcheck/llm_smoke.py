"""L3 lightweight LLM smoke · 单次最小往返,验真-LLM 通 + 报告延迟/token/估算成本.

`tagent doctor --llm-smoke` 5 秒验证,远轻于 --probe (16 agent 全跑 ~$0.3-0.8).
用 aux 通道 provider 隔离主 prompt cache ( 借鉴).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from loguru import logger

from runtime.config.settings import get_settings
from runtime.router.llm_client import PROVIDER_MODEL_MAP

SMOKE_SYSTEM = "You are a translation helper. Reply with ONLY the translated text, no extra words."
SMOKE_USER = "Translate to Chinese: Hello"


@dataclass(slots=True)
class SmokeResult:
    ok: bool
    provider: str
    model: str
    latency_ms: int
    response: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    reason: str = ""


def run_llm_smoke(provider: str | None = None) -> SmokeResult:
    """Single round-trip 'Hello → 你好' smoke.

    Resolves provider in order: explicit arg → TAGENT_AUX_PROVIDER → TAGENT_LLM_PROVIDER → settings.
    Returns metrics + cost without raising.
    """
    s = get_settings()
    prov = (
        provider
        or os.getenv("TAGENT_AUX_PROVIDER")
        or os.getenv("TAGENT_LLM_PROVIDER")
        or s.llm_provider
    )
    model = PROVIDER_MODEL_MAP.get(prov, prov)

    if prov == "stub":
        return SmokeResult(
            ok=True,
            provider=prov,
            model="stub",
            latency_ms=0,
            response="(stub) 你好",
            reason="stub provider — no real LLM called",
        )

    try:
        import litellm
    except ImportError:
        return SmokeResult(
            ok=False,
            provider=prov,
            model=model,
            latency_ms=0,
            reason="litellm not installed; pip install litellm",
        )

    t0 = time.time()
    try:
        resp = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": SMOKE_SYSTEM},
                {"role": "user", "content": SMOKE_USER},
            ],
            temperature=0.0,
            max_tokens=32,
            timeout=s.llm_timeout_seconds,
            num_retries=0,
        )
    except Exception as e:  # noqa: BLE001
        return SmokeResult(
            ok=False,
            provider=prov,
            model=model,
            latency_ms=int((time.time() - t0) * 1000),
            reason=f"{type(e).__name__}: {e}",
        )

    latency = int((time.time() - t0) * 1000)
    try:
        content = resp["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return SmokeResult(
            ok=False,
            provider=prov,
            model=model,
            latency_ms=latency,
            reason=f"malformed response: {resp!r}",
        )

    usage = (resp.get("usage") if isinstance(resp, dict) else getattr(resp, "usage", None)) or {}
    if not isinstance(usage, dict):
        usage = dict(getattr(usage, "__dict__", {}) or {})
    pt = int(usage.get("prompt_tokens", 0) or 0)
    ct = int(usage.get("completion_tokens", 0) or 0)

    cost = 0.0
    try:
        cost = float(litellm.completion_cost(completion_response=resp))
    except Exception as e:  # noqa: BLE001
        logger.debug("cost lookup failed: {}", e)

    body = content.strip()
    if not body:
        return SmokeResult(
            ok=False,
            provider=prov,
            model=model,
            latency_ms=latency,
            response=content,
            prompt_tokens=pt,
            completion_tokens=ct,
            cost_usd=cost,
            reason="empty response",
        )

    return SmokeResult(
        ok=True,
        provider=prov,
        model=model,
        latency_ms=latency,
        response=body,
        prompt_tokens=pt,
        completion_tokens=ct,
        cost_usd=cost,
    )
