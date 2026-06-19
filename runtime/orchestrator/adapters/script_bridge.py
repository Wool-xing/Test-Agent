"""Bridge standalone utils scripts into the orchestrator pipeline.

Each adapter wraps a standalone script with:
- Input normalization (DAG node inputs → CLI args / stdin JSON)
- Output parsing (stdout → structured dict)
- Graceful degradation (script not found → error result, not crash)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

from loguru import logger
from runtime.config.settings import get_settings


def _scripts_dir() -> Path:
    return get_settings().scripts_dir


def _run_script(script_name: str, args: list[str] | None = None,
                stdin_data: dict | None = None, timeout: int = 120) -> dict:
    """Execute a standalone script and return structured result."""
    script_path = _scripts_dir() / script_name
    if not script_path.exists():
        return {"ok": False, "error": f"script not found: {script_name}", "returncode": 127}

    cmd = [sys.executable, str(script_path), *(args or [])]
    try:
        stdin_str = json.dumps(stdin_data, ensure_ascii=False) if stdin_data else None
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=stdin_str,
        )
        return {
            "ok": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": r.stdout[-2000:],
            "stderr": r.stderr[-1000:],
            "command": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s", "returncode": 124}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "returncode": 1}


# ── Per-script adapters ──


def run_mutation_test(target: str = "src", **_) -> dict:
    """Run mutation testing via mutation_runner.py."""
    logger.info("bridge: mutation test target={}", target)
    return _run_script("mutation_runner.py", ["run", "--target", target], timeout=600)


def run_chaos_experiment(operation: str = "cpu-stress", **kwargs) -> dict:
    """Run chaos experiment via chaos_helper.py. Requires TAGENT_CHAOS_AUTHORIZED."""
    logger.info("bridge: chaos experiment op={}", operation)
    return _run_script("chaos_helper.py", [operation], stdin_data=kwargs, timeout=300)


def run_fuzz_http(target_url: str, **kwargs) -> dict:
    """Run HTTP fuzzing via fuzzer.py."""
    logger.info("bridge: fuzz target={}", target_url)
    return _run_script("fuzzer.py", ["fuzz", "--url", target_url],
                       stdin_data=kwargs, timeout=300)


def run_a11y_scan(target_url: str, **kwargs) -> dict:
    """Run accessibility scan via a11y_scanner.py."""
    logger.info("bridge: a11y scan target={}", target_url)
    return _run_script("a11y_scanner.py", ["scan", "--url", target_url],
                       stdin_data=kwargs, timeout=120)


def run_suite_minimize(test_file: str, strategy: str = "similarity", **kwargs) -> dict:
    """Run suite minimization via suite_minimizer.py."""
    logger.info("bridge: suite minimize file={} strategy={}", test_file, strategy)
    return _run_script("suite_minimizer.py", ["minimize", "--input", test_file,
                       "--strategy", strategy], stdin_data=kwargs, timeout=180)


def run_chaos_observe() -> dict:
    """Observe chaos experiment status without running new experiments."""
    return _run_script("chaos_helper.py", ["status"])


# ── Dynamic resolution ──

BRIDGE_MAP: dict[str, str] = {
    # Experts → scripts
    "mutation-test": "mutation_runner.py",
    "chaos-test": "chaos_helper.py",
    "fuzz-test": "fuzzer.py",
    "a11y-test": "a11y_scanner.py",
    "suite-minimize": "suite_minimizer.py",
    # Skills → scripts (reuse same scripts)
    "mutation-testing": "mutation_runner.py",
    "chaos-engineering": "chaos_helper.py",
    "api-fuzzing": "fuzzer.py",
    "accessibility-scan": "a11y_scanner.py",
    "test-suite-minimization": "suite_minimizer.py",
}

ADAPTER_MAP: dict[str, Callable] = {
    "mutation_runner.py": run_mutation_test,
    "chaos_helper.py": run_chaos_experiment,
    "fuzzer.py": run_fuzz_http,
    "a11y_scanner.py": run_a11y_scan,
    "suite_minimizer.py": run_suite_minimize,
}


def resolve_bridge(name: str) -> tuple[str | None, callable | None]:
    """Resolve expert/skill name → (script_name, adapter_fn)."""
    script = BRIDGE_MAP.get(name)
    if not script:
        return None, None
    return script, ADAPTER_MAP.get(script)
