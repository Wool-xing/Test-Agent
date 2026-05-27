"""Real-model router accuracy test (M2-7).

Charter §21:
  - 横切准则: 失败必带 seed + snapshot (固定 random seed)
  - 横切准则: 测试预算上限 (timeout per call)
  - 决策可追溯 §18-12: 每次失败入 decisions/

Run conditions:
  - Requires TAGENT_LLM_PROVIDER ∈ {claude, openai, gemini, qwen, deepseek, ollama}
  - Requires corresponding API key in env (per LiteLLM convention)
  - Skipped if provider == stub

Threshold:
  - Single model accuracy ≥ 85%
  - Two-model vote accuracy ≥ 95% (when 2 keys present)
"""

from __future__ import annotations

import json
import os
import random
import time
from pathlib import Path

import pytest

from runtime.config.settings import get_settings
from runtime.router.llm_client import LLMClient
from runtime.router.router import route, route_with_vote
from runtime.router.schema import TargetArtifact

RANDOM_SEED = 42  # §21 可复现性: 固定 seed
random.seed(RANDOM_SEED)

# 20 test samples: 4 types × 5 phrasings each
SAMPLES: list[tuple[str, str]] = [
    # web-system × 5
    ("测试 Web 应用 https://example.com 登录+支付完整流程", "web-system"),
    ("Help me test https://shop.example.com cart and checkout end-to-end", "web-system"),
    ("Web 系统功能测试,涵盖用户注册/登录/找回密码", "web-system"),
    ("浏览器跨浏览器测试,Chrome+Firefox+Safari 兼容验证", "web-system"),
    ("Test our React SPA dashboard for visual regression and a11y", "web-system"),
    # rest-api × 5
    ("REST API endpoints /v1/orders /v1/users gRPC + WebSocket performance test", "rest-api"),
    ("我需要对接口做契约测试,OpenAPI spec 已提供", "rest-api"),
    ("API 安全测试: SQL 注入 + XSS + 越权访问检测", "rest-api"),
    ("GraphQL API endpoint /graphql performance and N+1 query check", "rest-api"),
    ("gRPC service health check + load test up to 5000 QPS", "rest-api"),
    # mobile-app × 5
    ("Test Android APK release build, focus on UI + push notification", "mobile-app"),
    ("iOS IPA TestFlight build needs full functional regression", "mobile-app"),
    ("移动端 app.apk 安装测试 + 弱网环境下的稳定性", "mobile-app"),
    ("微信小程序 wxapp.zip 完整测试,含支付+登录授权", "mobile-app"),
    ("Mobile app battery + memory leak profiling on Android", "mobile-app"),
    # ai-model × 5
    ("LLM application evaluation: hallucination rate + prompt injection robustness", "ai-model"),
    ("AI 模型质量回归 + 数据漂移检测 + 公平性偏见审计", "ai-model"),
    ("Test our RAG pipeline retrieval recall and answer faithfulness", "ai-model"),
    ("ML model accuracy + adversarial robustness on production traffic", "ai-model"),
    ("Evaluate fine-tuned model card completeness + backdoor detection", "ai-model"),
]


def _decisions_log(record: dict) -> Path:
    """Charter §18-12 决策可追溯: log each routing decision."""
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "执行日志" / "decisions"
    d.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    target = d / f"{ts}_router_real_test_{record.get('sample_id', 'x')}.json"
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _provider_available(provider: str) -> bool:
    if provider == "stub":
        return False
    # 通用 OpenAI 兼容: TAGENT_LLM_API_KEY 设 = 任厂商即插即用 (国内+国外不限)
    if os.getenv("TAGENT_LLM_API_KEY"):
        return True
    keys = {
        "claude": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "qwen": "DASHSCOPE_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "ollama": None,  # local, assume available if env explicitly set
    }
    k = keys.get(provider)
    if k is None:
        return os.getenv("TAGENT_LLM_PROVIDER") == "ollama"
    return bool(os.getenv(k))


@pytest.mark.skipif(
    os.getenv("TAGENT_LLM_PROVIDER", "stub") == "stub",
    reason="Real LLM not configured; set TAGENT_LLM_PROVIDER + API key",
)
def test_router_single_model_accuracy_85pct():
    provider = os.getenv("TAGENT_LLM_PROVIDER")
    if not _provider_available(provider):
        pytest.skip(f"provider {provider} requires API key in env")

    client = LLMClient(provider=provider, fallback="stub")
    correct = 0
    failures: list[dict] = []
    for i, (text, expected) in enumerate(SAMPLES):
        art = TargetArtifact(kind="text", text=text)
        t0 = time.monotonic()
        try:
            d = route(art, client=client, use_history=False)
            elapsed = time.monotonic() - t0
            ok = d.detected_target_type == expected
            if ok:
                correct += 1
            else:
                failures.append(
                    {
                        "sample_id": i,
                        "text": text,
                        "expected": expected,
                        "got": d.detected_target_type,
                        "confidence": d.confidence,
                        "elapsed_s": elapsed,
                        "seed": RANDOM_SEED,
                        "provider": provider,
                    }
                )
        except Exception as e:
            failures.append({"sample_id": i, "text": text, "error": str(e), "seed": RANDOM_SEED, "provider": provider})

    accuracy = correct / len(SAMPLES)
    record = {
        "test": "single_model",
        "provider": provider,
        "total": len(SAMPLES),
        "correct": correct,
        "accuracy": accuracy,
        "seed": RANDOM_SEED,
        "failures": failures,
    }
    _decisions_log(record)
    print(f"\n[single-model {provider}] accuracy = {accuracy:.2%} ({correct}/{len(SAMPLES)})")
    assert accuracy >= 0.85, f"single-model accuracy {accuracy:.2%} < 85%; failures dumped to decisions/"


@pytest.mark.skipif(
    not (_provider_available("claude") and _provider_available("qwen")),
    reason="Two-model vote needs both ANTHROPIC_API_KEY and DASHSCOPE_API_KEY",
)
def test_router_two_model_vote_95pct():
    correct = 0
    failures: list[dict] = []
    for i, (text, expected) in enumerate(SAMPLES):
        art = TargetArtifact(kind="text", text=text)
        try:
            d = route_with_vote(art, providers=["claude", "qwen"])
            if d.detected_target_type == expected:
                correct += 1
            else:
                failures.append(
                    {
                        "sample_id": i,
                        "text": text,
                        "expected": expected,
                        "got": d.detected_target_type,
                        "confidence": d.confidence,
                        "seed": RANDOM_SEED,
                    }
                )
        except Exception as e:
            failures.append({"sample_id": i, "text": text, "error": str(e), "seed": RANDOM_SEED})

    accuracy = correct / len(SAMPLES)
    record = {
        "test": "two_model_vote",
        "providers": ["claude", "qwen"],
        "total": len(SAMPLES),
        "correct": correct,
        "accuracy": accuracy,
        "seed": RANDOM_SEED,
        "failures": failures,
    }
    _decisions_log(record)
    print(f"\n[vote claude+qwen] accuracy = {accuracy:.2%} ({correct}/{len(SAMPLES)})")
    assert accuracy >= 0.95, f"two-model vote accuracy {accuracy:.2%} < 95%; failures dumped"
