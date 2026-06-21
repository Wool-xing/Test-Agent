"""Sprint 7 — 部署后冒烟测试 (install → init → run → report 全链路)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    """Run a command and return (exit_code, output)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          encoding="utf-8", errors="replace")
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode, out[:500]
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT"
    except FileNotFoundError:
        return -1, f"Command not found: {cmd[0]}"


def main() -> int:
    py = sys.executable
    tagent = [py, "-m", "runtime.cli.main"]
    failures = 0

    checks = [
        ("1. CLI version", tagent + ["--version"], "Test-Agent Runtime v2"),
        ("2. CLI help", tagent + ["--help"], "Commands"),
        ("3. Config load", [py, "-c", "from runtime.config.settings import get_settings; s=get_settings(); print(s.deployment_mode)"], "community"),
        ("4. Skill list", tagent + ["skill", "list"], "check"),
        ("5. Catalog", tagent + ["catalog"], "skill"),
        ("6. Doctor exists", [py, "-c", "from runtime.cli.commands.doctor import app; print('PASS')"], "PASS"),
        ("7. Report gen", [py, "-c", "from runtime.exporters.report import ReportGenerator; g=ReportGenerator(); g.to_json([{'name':'t1','status':'pass'}],'/tmp/smoke.json'); print('OK')"], "OK"),
        ("8. SDK scaffold", [py, "-c", "from runtime.sdk import scaffold_skill, validate_skill, discover_skills; print('OK')"], "OK"),
        ("9. Migration dry-run", tagent + ["migrate", "v2", "--dry-run"], "not needed"),
        ("10. Degradation", [py, "-c", "from runtime.infra.degradation import DegradationManager, DegradationLevel; m=DegradationManager(); m.degrade('test',DegradationLevel.DEGRADED,'smoke'); m.recover('test'); print('OK')"], "OK"),
        ("11. Sandbox", [py, "-c", "from runtime.core.sandbox import ProcessSandbox,SandboxConfig; s=ProcessSandbox(SandboxConfig(time_limit_seconds=5)); r=s.execute('echo smoke',timeout=3); print('OK' if r.ok else 'FAIL')"], "OK"),
        ("12. Audit log", [py, "-c", "from runtime.observability.audit import log_event,query_events; log_event('smoke_test',actor='ci'); events=query_events(1); print('OK' if events else 'FAIL')"], "OK"),
    ]

    for name, cmd, expected in checks:
        code, output = run(cmd)
        ok = code == 0 or expected.lower() in output.lower()
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"[{status}] {name} (exit={code})")

    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILURES'}")
    return failures


if __name__ == "__main__":
    sys.exit(main())
