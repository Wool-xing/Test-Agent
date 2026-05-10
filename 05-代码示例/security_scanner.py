"""
安全扫描：SAST（代码静态分析）+ DAST（运行时扫描）+ 依赖漏洞 + Header / TLS
被引用方：15-安全测试 agent / security-test skill
依赖（按需）：bandit / safety / requests / OWASP ZAP API
"""
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# ===== SAST：Bandit（Python 代码静态扫描）=====

def run_bandit(target_path: str, output: Optional[str] = None) -> Dict:
    """Bandit Python SAST。需 pip install bandit"""
    output = output or "workspace/执行日志/security/bandit_report.json"
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    cmd = ["bandit", "-r", target_path, "-f", "json", "-o", output, "-q"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if not Path(output).exists():
        return {"error": "bandit 输出无文件", "stderr": proc.stderr}
    data = json.loads(Path(output).read_text(encoding="utf-8"))
    high = sum(1 for r in data.get("results", []) if r.get("issue_severity") == "HIGH")
    medium = sum(1 for r in data.get("results", []) if r.get("issue_severity") == "MEDIUM")
    return {
        "total_issues": len(data.get("results", [])),
        "high": high, "medium": medium,
        "low": len(data.get("results", [])) - high - medium,
        "report": output,
    }


# ===== 依赖漏洞：Safety（Python pip）=====

def run_safety_check(requirements_file: str = "requirements.txt") -> Dict:
    """Safety 检查 pip 依赖 CVE。需 pip install safety"""
    cmd = ["safety", "check", "-r", requirements_file, "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    try:
        data = json.loads(proc.stdout) if proc.stdout else {"vulnerabilities": []}
    except json.JSONDecodeError:
        return {"error": "safety 输出解析失败", "raw": proc.stdout[:500]}
    vulns = data.get("vulnerabilities", [])
    return {
        "vulnerabilities_count": len(vulns),
        "high": sum(1 for v in vulns if v.get("severity") == "high"),
        "details": vulns,
    }


# ===== HTTP 安全 Header 检查 =====

REQUIRED_SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Referrer-Policy",
]


def check_security_headers(url: str, timeout: int = 10) -> Dict:
    """检查目标 URL 的安全响应头"""
    r = requests.get(url, timeout=timeout, allow_redirects=True)
    missing = [h for h in REQUIRED_SECURITY_HEADERS if h not in r.headers]
    return {
        "url": url,
        "status_code": r.status_code,
        "missing_headers": missing,
        "present_headers": {h: r.headers.get(h) for h in REQUIRED_SECURITY_HEADERS if h in r.headers},
        "score": round((len(REQUIRED_SECURITY_HEADERS) - len(missing)) / len(REQUIRED_SECURITY_HEADERS) * 100, 1),
    }


# ===== TLS / SSL 证书检查 =====

def check_tls_cert(host: str, port: int = 443) -> Dict:
    import socket
    import ssl
    from datetime import datetime

    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            cert = ssock.getpeercert()
    not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
    days_left = (not_after - datetime.utcnow()).days
    return {
        "host": host,
        "issuer": dict(x[0] for x in cert["issuer"]),
        "subject": dict(x[0] for x in cert["subject"]),
        "not_after": cert["notAfter"],
        "days_to_expire": days_left,
        "is_expiring_soon": days_left < 30,
    }


# ===== Burp Suite Pro REST API 集成 =====

def burp_active_scan(target_url: str,
                     burp_api: Optional[str] = None,
                     api_key: Optional[str] = None,
                     timeout: int = 1800,
                     poll_interval: int = 30) -> Dict:
    """
    Burp Suite Professional REST API 扫描。
    需启 Burp Pro + 启用 REST API（User options → Misc → REST API）。
    burp_api: 默认 http://127.0.0.1:1337
    api_key: User options → REST API → API key
    """
    import time
    base = (burp_api or os.getenv("BURP_API_URL", "http://127.0.0.1:1337")).rstrip("/")
    key = api_key or os.getenv("BURP_API_KEY", "")

    # API key 在 URL path 中（Burp 协议）
    base_with_key = f"{base}/{key}" if key else base

    # 1. 启动扫描
    r = requests.post(f"{base_with_key}/v0.1/scan", json={
        "urls": [target_url],
        "scan_configurations": [{"name": "Crawl and Audit - Lightweight", "type": "NamedConfiguration"}],
    }, timeout=30)
    r.raise_for_status()
    task_id = r.headers.get("Location", "").rstrip("/").split("/")[-1]
    if not task_id:
        return {"error": "未获取到 task_id", "response": r.text[:500]}

    logger.info(f"Burp 扫描启动 task_id={task_id}")

    # 2. 轮询状态
    end = time.time() + timeout
    last_status = None
    while time.time() < end:
        s = requests.get(f"{base_with_key}/v0.1/scan/{task_id}", timeout=10).json()
        status = s.get("scan_status")
        last_status = s
        if status == "succeeded":
            break
        if status == "failed":
            return {"error": "Burp scan failed", "details": s}
        time.sleep(poll_interval)

    if not last_status:
        return {"error": "扫描超时"}

    # 3. 解析告警
    issues = last_status.get("issue_events", [])
    by_severity = {"high": 0, "medium": 0, "low": 0, "info": 0}
    issue_summaries = []
    for evt in issues:
        issue = evt.get("issue", {})
        sev = (issue.get("severity") or "info").lower()
        by_severity[sev] = by_severity.get(sev, 0) + 1
        issue_summaries.append({
            "name": issue.get("name"),
            "severity": sev,
            "confidence": issue.get("confidence"),
            "url": issue.get("origin", "") + issue.get("path", ""),
        })

    return {
        "target": target_url,
        "task_id": task_id,
        "total_issues": len(issues),
        "by_severity": by_severity,
        "issues": issue_summaries[:50],
    }


def burp_proxy_listen(host: str = "127.0.0.1", port: int = 8080) -> Dict:
    """返回 Burp 代理监听信息（供测试脚本通过此代理跑用例 → Burp 自动收集流量）。
    注意：测试脚本需要把 HTTP_PROXY/HTTPS_PROXY 指向此地址。
    """
    return {
        "proxy_url": f"http://{host}:{port}",
        "usage": "在测试脚本环境变量设置 HTTPS_PROXY=http://127.0.0.1:8080 + 信任 Burp CA 证书",
    }


# ===== OWASP ZAP DAST 集成（可选，需启 ZAP daemon）=====

def zap_active_scan(target_url: str, zap_api: str = "http://localhost:8080",
                    api_key: Optional[str] = None, timeout: int = 600) -> Dict:
    """触发 ZAP 主动扫描。前提：本地启 ZAP daemon（zap.sh -daemon -port 8080）"""
    import time
    api_key = api_key or os.getenv("ZAP_API_KEY", "")
    params = {"url": target_url, "apikey": api_key}

    # 1. spider
    requests.get(f"{zap_api}/JSON/spider/action/scan/", params=params, timeout=30)
    # 2. active scan
    r = requests.get(f"{zap_api}/JSON/ascan/action/scan/", params=params, timeout=30)
    scan_id = r.json().get("scan")

    # 3. poll
    end = time.time() + timeout
    while time.time() < end:
        s = requests.get(f"{zap_api}/JSON/ascan/view/status/",
                         params={"scanId": scan_id, "apikey": api_key}, timeout=10).json()
        if int(s.get("status", 0)) >= 100:
            break
        time.sleep(10)

    # 4. 取告警
    alerts = requests.get(f"{zap_api}/JSON/core/view/alerts/",
                          params={"baseurl": target_url, "apikey": api_key}, timeout=30).json().get("alerts", [])
    by_risk = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
    for a in alerts:
        by_risk[a.get("risk", "Informational")] = by_risk.get(a.get("risk"), 0) + 1
    return {
        "target": target_url,
        "total_alerts": len(alerts),
        "by_risk": by_risk,
        "alerts": alerts[:50],   # 仅返回前 50
    }


# ===== CLI =====

def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="安全扫描工具")
    sub = parser.add_subparsers(dest="cmd")

    bd = sub.add_parser("bandit"); bd.add_argument("target")
    sf = sub.add_parser("safety"); sf.add_argument("--req", default="requirements.txt")
    hd = sub.add_parser("headers"); hd.add_argument("url")
    tls = sub.add_parser("tls"); tls.add_argument("host"); tls.add_argument("--port", type=int, default=443)
    zap = sub.add_parser("zap"); zap.add_argument("url")
    burp = sub.add_parser("burp"); burp.add_argument("url"); burp.add_argument("--timeout", type=int, default=1800)

    args = parser.parse_args()
    if args.cmd == "bandit":
        print(json.dumps(run_bandit(args.target), indent=2))
    elif args.cmd == "safety":
        print(json.dumps(run_safety_check(args.req), indent=2))
    elif args.cmd == "headers":
        print(json.dumps(check_security_headers(args.url), indent=2, ensure_ascii=False))
    elif args.cmd == "tls":
        print(json.dumps(check_tls_cert(args.host, args.port), indent=2, default=str))
    elif args.cmd == "zap":
        print(json.dumps(zap_active_scan(args.url), indent=2, ensure_ascii=False))
    elif args.cmd == "burp":
        print(json.dumps(burp_active_scan(args.url, timeout=args.timeout), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
