"""L3 LLM probe · 每个 agent 真 LLM 调一次最简任务,验证可达性 + 响应非空.

成本:16 agent × 1 short call ≈ $0.3-0.8(模型 / 输入大小 而定).
仅 `tagent doctor --agents --probe` 触发,默认关。
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from runtime.registry.registry import build_catalog
from runtime.subagent.aux_client import aux_client

SMOKE_PROMPT = "用一句话(≤30 字)用中文描述你这个测试专家的核心职责。不要任何前置废话。"


@dataclass(slots=True)
class ProbeResult:
    name: str
    ok: bool
    latency_ms: int
    reason: str = ""


def _probe_one(client, agent_name: str, agent_desc: str) -> ProbeResult:
    sys_prompt = f"你扮演 Test-Agent 项目内 `{agent_name}` 专家。原描述:{agent_desc[:200]}"
    t0 = time.time()
    try:
        reply = client.complete(sys_prompt, SMOKE_PROMPT, max_tokens=80, temperature=0.0)
    except Exception as e:  # noqa: BLE001
        return ProbeResult(name=agent_name, ok=False, latency_ms=int((time.time() - t0) * 1000), reason=f"raised: {e}")
    elapsed = int((time.time() - t0) * 1000)
    if not reply or not reply.strip():
        return ProbeResult(name=agent_name, ok=False, latency_ms=elapsed, reason="empty response")
    if len(reply.strip()) < 4:
        return ProbeResult(name=agent_name, ok=False, latency_ms=elapsed, reason=f"too short: {reply!r}")
    return ProbeResult(name=agent_name, ok=True, latency_ms=elapsed)


def probe_all_agents() -> list[ProbeResult]:
    cat = build_catalog()
    client = aux_client()
    out: list[ProbeResult] = []
    for name, entry in sorted(cat.experts.items()):
        out.append(_probe_one(client, name, entry.description))
    return out
