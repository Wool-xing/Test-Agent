"""ping-check skill: ICMP ping latency test."""
import argparse
import subprocess
import sys
import time
import json
import platform


def ping_host(host: str, count: int = 4, timeout: int = 30) -> dict:
    param = "-n" if platform.system() == "Windows" else "-c"
    deadline = ["-w", str(timeout * 1000)] if platform.system() == "Windows" else ["-W", str(timeout)]
    try:
        start = time.monotonic()
        result = subprocess.run(
            ["ping", param, str(count), *deadline, host],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        ok = result.returncode == 0
        return {
            "ok": ok,
            "host": host,
            "latency_ms": elapsed_ms,
            "output": result.stdout[-500:] if result.stdout else "",
            "error": result.stderr[:500] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "host": host, "error": "timeout", "latency_ms": timeout * 1000}
    except Exception as e:
        return {"ok": False, "host": host, "error": str(e)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True, help="Target hostname or IP")
    parser.add_argument("--count", type=int, default=4, help="Ping count")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout seconds")
    args = parser.parse_args()
    result = ping_host(args.host, args.count, args.timeout)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)
