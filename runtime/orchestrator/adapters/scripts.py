"""Adapter: wrap `utils/*.py` scripts as callable units.

Uses subprocess to isolate sys.path / globals from the runtime layer.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from runtime.config.settings import get_settings
from runtime.self_healing.retry import with_retry


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
    """Run a script under utils/ by filename.

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
        # scripts are organized into subdirs (utils/reporting/, utils/data/, ...).
        # Recursively look up by basename when not at top-level.
        matches = [p for p in scripts_dir.rglob(script_filename) if p.is_file()]
        if len(matches) == 1:
            script_path = matches[0]
        elif len(matches) > 1:
            raise FileNotFoundError(
                f"ambiguous script {script_filename}: {[str(m.relative_to(scripts_dir)) for m in matches]}"
            )
        else:
            raise FileNotFoundError(f"script not found: {script_path}")
    cmd = [sys.executable, str(script_path), *(args or [])]
    logger.info("running script: {}", " ".join(cmd))
    start = time.monotonic()

    def _do_run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8"},
        )

    proc = with_retry(_do_run)()
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
    # scripts are organized in subdirs (utils/reporting/, utils/data/, ...).
    # Return basenames so callers can run_script("excel_generator.py") regardless of subdir.
    seen: set[str] = set()
    for p in scripts_dir.rglob("*.py"):
        if p.name.startswith("_"):
            continue
        seen.add(p.name)
    return sorted(seen)
