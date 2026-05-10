"""
契约测试（Contract Testing） - 微服务消费者-提供者契约
被引用方：API 测试 / 微服务集成

实现方式：
1. Pact（推荐）：消费者写 pact 文件，提供者验证
2. 简化 schema 验证（jsonschema）：HTTP 响应符合契约
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# ===== JSON Schema 契约验证 =====

def verify_response_schema(url: str, expected_schema: Dict,
                           method: str = "GET", **request_kwargs) -> Dict:
    """
    用 jsonschema 验证 HTTP 响应符合契约。
    expected_schema: 标准 JSON Schema
    """
    try:
        from jsonschema import validate, ValidationError
    except ImportError:
        raise RuntimeError("jsonschema 未安装：pip install jsonschema")

    r = requests.request(method, url, **request_kwargs, timeout=10)
    body = r.json()
    try:
        validate(instance=body, schema=expected_schema)
        return {"url": url, "valid": True, "status_code": r.status_code}
    except ValidationError as e:
        return {
            "url": url,
            "valid": False,
            "status_code": r.status_code,
            "error": str(e),
            "path": list(e.path),
        }


# ===== Pact 模式（仅骨架）=====

def generate_pact_consumer_stub(consumer: str, provider: str,
                                 interactions: List[Dict],
                                 output: str = "workspace/自动化脚本/python/pacts") -> str:
    """
    生成 Pact JSON 文件骨架。生产中应用 pact-python 库 mock_service。
    interactions: [{"description": "...", "request": {...}, "response": {...}}]
    """
    pact = {
        "consumer": {"name": consumer},
        "provider": {"name": provider},
        "interactions": interactions,
        "metadata": {"pactSpecification": {"version": "3.0.0"}},
    }
    Path(output).mkdir(parents=True, exist_ok=True)
    path = Path(output) / f"{consumer}-{provider}.json"
    path.write_text(json.dumps(pact, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Pact 文件已生成: {path}")
    return str(path)


# ===== Provider 端验证 Pact =====

def verify_pact_provider(pact_file: str, provider_url: str) -> Dict:
    """
    简化版 Provider 验证：读取 pact 文件，逐个 interaction 重放，验响应。
    生产用 pact-python verifier。
    """
    pact = json.loads(Path(pact_file).read_text(encoding="utf-8"))
    results = []
    for inter in pact.get("interactions", []):
        req = inter["request"]
        method = req.get("method", "GET")
        path = req.get("path", "/")
        body = req.get("body")
        url = provider_url.rstrip("/") + path

        try:
            r = requests.request(method, url, json=body, timeout=10)
            expected_status = inter["response"].get("status", 200)
            results.append({
                "description": inter.get("description"),
                "expected_status": expected_status,
                "actual_status": r.status_code,
                "match": r.status_code == expected_status,
            })
        except Exception as e:
            results.append({"description": inter.get("description"),
                            "error": str(e), "match": False})

    return {"total": len(results), "matched": sum(1 for r in results if r.get("match")),
            "details": results}


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="契约测试")
    sub = parser.add_subparsers(dest="cmd")
    v = sub.add_parser("verify"); v.add_argument("pact"); v.add_argument("provider_url")
    args = parser.parse_args()
    if args.cmd == "verify":
        print(json.dumps(verify_pact_provider(args.pact, args.provider_url), indent=2, ensure_ascii=False))
