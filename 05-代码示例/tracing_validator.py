"""
链路追踪校验：Jaeger / Zipkin HTTP API
被引用方：13-系统集成测试 agent
"""
import logging
import os
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class JaegerClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("JAEGER_BASE_URL", "")).rstrip("/")
        if not self.base_url:
            raise ValueError("JAEGER_BASE_URL 未配置")

    def get_trace(self, trace_id: str) -> List[Dict]:
        """返回 trace 中所有 span"""
        url = f"{self.base_url}/api/traces/{trace_id}"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            return []
        return data[0].get("spans", [])

    def services(self) -> List[str]:
        url = f"{self.base_url}/api/services"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json().get("data", [])

    def search_traces(self, service: str, operation: Optional[str] = None,
                      lookback_minutes: int = 60, limit: int = 20) -> List[List[Dict]]:
        """按 service 查询 trace 列表"""
        params = {
            "service": service,
            "lookback": f"{lookback_minutes}m",
            "limit": limit,
        }
        if operation:
            params["operation"] = operation
        url = f"{self.base_url}/api/traces"
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return [t.get("spans", []) for t in r.json().get("data", [])]


def assert_trace_complete(client: JaegerClient, trace_id: str,
                          required_services: set,
                          max_duration_ms: Optional[int] = None) -> Dict:
    """
    断言 trace 包含全部 required_services，可选总耗时上限。
    返回 {pass, services_found, duration_ms}
    """
    spans = client.get_trace(trace_id)
    services_found = {s.get("process", {}).get("serviceName") for s in spans if s.get("process")}

    duration_us = (
        max(s["startTime"] + s["duration"] for s in spans)
        - min(s["startTime"] for s in spans)
    ) if spans else 0
    duration_ms = duration_us / 1000

    pass_services = required_services.issubset(services_found)
    pass_duration = (max_duration_ms is None) or (duration_ms <= max_duration_ms)

    return {
        "pass": pass_services and pass_duration,
        "services_found": sorted(services_found),
        "missing_services": sorted(required_services - services_found),
        "duration_ms": round(duration_ms, 1),
        "max_duration_ms": max_duration_ms,
    }


# ===== CLI =====

if __name__ == "__main__":
    import argparse
    import json as _json
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_id")
    parser.add_argument("--required-services", nargs="+", required=True)
    parser.add_argument("--max-duration-ms", type=int, default=None)
    args = parser.parse_args()
    client = JaegerClient()
    print(_json.dumps(
        assert_trace_complete(client, args.trace_id, set(args.required_services), args.max_duration_ms),
        indent=2, ensure_ascii=False,
    ))
