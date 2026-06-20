"""http-check skill: HTTP endpoint health test."""
import argparse
import ipaddress
import socket
import sys
import json
import time
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _validate_url(url: str) -> str | None:
    """Validate URL is safe (http/https only, no private IPs). Returns error or None."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"unsupported scheme: {parsed.scheme}"
    if not parsed.hostname:
        return "missing hostname"
    try:
        addr = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        try:
            addr = ipaddress.ip_address(socket.gethostbyname(parsed.hostname))
        except (socket.gaierror, ValueError):
            return None  # DNS resolution failure; let urlopen handle it
    for net in _PRIVATE_RANGES:
        if addr in net:
            return f"private/internal IP blocked: {addr}"
    return None


def check_http(url: str, method: str = "GET", expected_status: int = 200, timeout: int = 30) -> dict:
    error = _validate_url(url)
    if error:
        return {"ok": False, "url": url, "error": error}
    try:
        start = time.monotonic()
        req = Request(url, method=method, headers={"User-Agent": "Test-Agent/2.0"})
        resp = urlopen(req, timeout=timeout)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "ok": resp.status == expected_status,
            "url": url,
            "status_code": resp.status,
            "expected_status": expected_status,
            "response_time_ms": elapsed_ms,
            "body_size": len(resp.read()),
        }
    except HTTPError as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {"ok": e.code == expected_status, "url": url, "status_code": e.code, "expected_status": expected_status, "response_time_ms": elapsed_ms, "error": str(e)}
    except URLError as e:
        return {"ok": False, "url": url, "error": str(e.reason)}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Target URL")
    parser.add_argument("--method", default="GET", help="HTTP method")
    parser.add_argument("--expected-status", type=int, default=200, dest="expected_status")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    result = check_http(args.url, args.method, args.expected_status, args.timeout)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)
