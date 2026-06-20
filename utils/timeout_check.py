"""timeout-check skill: verify operation completes within time limit."""
import argparse
import sys
import json
import time
import subprocess


def check_timeout(command: str, timeout: int = 30) -> dict:
    try:
        start = time.monotonic()
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "ok": True,
            "command": command,
            "elapsed_ms": elapsed_ms,
            "timeout_ms": timeout * 1000,
            "exit_code": result.returncode,
            "stdout": result.stdout[:500],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "command": command, "error": f"timed out after {timeout}s", "elapsed_ms": timeout * 1000}
    except Exception as e:
        return {"ok": False, "command": command, "error": str(e)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", required=True, help="Command to execute")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    args = parser.parse_args()
    result = check_timeout(args.command, args.timeout)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)
