"""http-check skill: HTTP endpoint health test."""
import argparse, sys, json, time
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def check_http(url: str, method: str = "GET", expected_status: int = 200, timeout: int = 30) -> dict:
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
