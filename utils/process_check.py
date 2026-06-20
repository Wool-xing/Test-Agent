"""process-check skill: check if a process is running."""
import argparse
import sys
import json
import subprocess
import platform


def check_process(name: str, expected_running: bool = True) -> dict:
    try:
        if platform.system() == "Windows":
            cmd = ["tasklist", "/FI", f"IMAGENAME eq {name}"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            running = result.returncode == 0 and name.lower() in result.stdout.lower()
        else:
            cmd = ["pgrep", "-x", name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            running = result.returncode == 0
        ok = running == expected_running
        return {"ok": ok, "process": name, "running": running, "expected_running": expected_running}
    except Exception as e:
        return {"ok": False, "process": name, "error": str(e)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Process name")
    parser.add_argument("--expected-running", type=lambda x: x.lower() == "true", default=True, dest="expected_running")
    args = parser.parse_args()
    result = check_process(args.name, args.expected_running)
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)
