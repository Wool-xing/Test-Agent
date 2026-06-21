"""Cross-environment test orchestration — run same suite across envs.

Sequential execution: test → staging (stops if test fails).
Uses env presets to switch config between runs.
Reports per-environment results with diff.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from runtime.config.settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_CHAIN = ["test", "staging"]


@dataclass
class EnvResult:
    env: str
    ok: bool
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    duration_ms: int = 0
    error: str = ""


@dataclass
class CrossEnvReport:
    results: list[EnvResult] = field(default_factory=list)
    all_passed: bool = True

    @property
    def summary(self) -> str:
        parts = []
        for r in self.results:
            icon = "✓" if r.ok else "✗"
            parts.append(f"{icon} {r.env}: {r.succeeded}/{r.total}")
        return " → ".join(parts)


def _last_baseline_dir() -> Path:
    d = get_settings().reports_dir / "cross_env"
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_cross_env(
    prompt: str,
    envs: list[str] | None = None,
    stop_on_fail: bool = True,
) -> CrossEnvReport:
    """Run the same test prompt across environments sequentially.

    Args:
        prompt: Natural language test request
        envs: List of environment preset names (default: test, staging)
        stop_on_fail: If True, stop after first failure
    """
    if envs is None:
        envs = DEFAULT_CHAIN

    report = CrossEnvReport()
    tagent_cmd = [sys.executable, "-X", "utf8", "-m", "runtime.cli.main"]

    for env_name in envs:
        t0 = time.time()

        # Load env preset
        from runtime.cli.env_presets import load_preset
        preset = load_preset(env_name)

        if preset is None:
            r = EnvResult(env=env_name, ok=False, error=f"env preset '{env_name}' not found")
            report.results.append(r)
            if stop_on_fail:
                break
            continue

        # Run test
        try:
            res = subprocess.run(
                tagent_cmd + ["selftest", "--e2e"],
                capture_output=True, text=True, timeout=300,
                env={**__import__("os").environ, **preset.env_vars},
            )
            ok = res.returncode == 0
            dur = int((time.time() - t0) * 1000)

            # Parse output for pass/fail counts
            total = succeeded = failed = 0
            for line in res.stdout.splitlines():
                if "ok" in line.lower() and "/" in line:
                    import re
                    m = re.search(r"(\d+)/(\d+)\s*ok", line)
                    if m:
                        succeeded = int(m.group(1))
                        total = int(m.group(2))
                        failed = total - succeeded

            r = EnvResult(env=env_name, ok=ok, total=total, succeeded=succeeded, failed=failed, duration_ms=dur)
            logger.info("cross-env %s: %s", env_name, "PASS" if ok else "FAIL")

        except subprocess.TimeoutExpired:
            r = EnvResult(env=env_name, ok=False, error="timeout (300s)")
        except Exception as e:
            r = EnvResult(env=env_name, ok=False, error=str(e)[:200])

        report.results.append(r)
        if not r.ok and stop_on_fail:
            break

    report.all_passed = all(r.ok for r in report.results)
    return report
