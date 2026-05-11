"""Adapter: wrap `05-代码示例/*.py` scripts as callable units.

Uses subprocess to isolate sys.path / globals from the runtime layer.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from runtime.config.settings import get_settings


@dataclass(slots=True)
class ScriptResult:
    script: str
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_script(script_filename: str, args: list[str] | None = None, *, timeout: int = 1800) -> ScriptResult:
    """Run a script under 05-代码示例/ by filename.

    Args:
        script_filename: e.g. "smoke_runner.py" (must live under scripts_dir).
        args: extra argv.
        timeout: seconds.
    """
    import time

    s = get_settings()
    scripts_dir: Path = s.resolve(s.scripts_dir)
    script_path = scripts_dir / script_filename
    if not script_path.is_file():
        raise FileNotFoundError(f"script not found: {script_path}")
    cmd = [sys.executable, str(script_path), *(args or [])]
    logger.info("running script: {}", " ".join(cmd))
    start = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    dur_ms = int((time.monotonic() - start) * 1000)
    return ScriptResult(
        script=script_filename,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        duration_ms=dur_ms,
    )


def list_available_scripts() -> list[str]:
    s = get_settings()
    scripts_dir: Path = s.resolve(s.scripts_dir)
    return sorted(p.name for p in scripts_dir.glob("*.py") if not p.name.startswith("_"))
