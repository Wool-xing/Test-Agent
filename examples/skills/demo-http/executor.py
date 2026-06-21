"""Demo HTTP Check executor — minimal example for Skill SDK."""

from __future__ import annotations

import time
import urllib.request
import urllib.error


def execute(params: dict, ctx) -> dict:
    """Execute an HTTP health check.

    Args:
        params: Dict with 'url' (required), 'expected_status' (default 200), 'timeout' (default 10).
        ctx: Execution context (unused in this demo).

    Returns:
        Dict with status, summary, details, checks, error.
    """
    url = params.get("url", "")
    if not url:
        return {"status": "error", "summary": "Missing required parameter: url", "details": {}, "checks": [], "error": "HTTP-001: url is required"}

    expected = int(params.get("expected_status", 200))
    timeout = min(int(params.get("timeout", 10)), 30)

    try:
        start = time.monotonic()
        req = urllib.request.Request(url, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=timeout)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        actual = resp.getcode()
        passed = actual == expected
        return {
            "status": "pass" if passed else "fail",
            "summary": f"{url} returned {actual} in {elapsed_ms}ms",
            "details": {"url": url, "status_code": actual, "response_time_ms": elapsed_ms},
            "checks": [
                {"name": "Status Code", "expected": expected, "actual": actual, "pass": passed},
                {"name": "Response Time", "expected": f"<{timeout}s", "actual": f"{elapsed_ms}ms", "pass": elapsed_ms < timeout * 1000},
            ],
            "error": None,
        }
    except urllib.error.URLError as e:
        return {"status": "error", "summary": f"Connection failed: {e.reason}", "details": {}, "checks": [], "error": f"HTTP-002: {e.reason}"}
    except ValueError:
        return {"status": "error", "summary": f"Invalid URL: {url}", "details": {}, "checks": [], "error": "HTTP-001: Invalid URL format"}
