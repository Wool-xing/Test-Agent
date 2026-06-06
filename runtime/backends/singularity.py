"""Singularity / Apptainer backend (hermes §1.4; HPC-friendly)."""

from __future__ import annotations

import asyncio
import shlex
import time
from pathlib import Path

from runtime.backends.base import BaseExecutionEnv, ExecResult, register


@register("singularity")
class SingularityBackend(BaseExecutionEnv):
    """Run commands inside a Singularity/Apptainer container image.

    Requires `singularity` or `apptainer` binary on PATH.
    """

    def __init__(self, image: str, *, binds: list[str] | None = None) -> None:
        self.image = image
        self.binds = binds or []

    async def connect(self) -> None:
        pass

    async def _run(self, argv: list[str], *, timeout: float = 120.0) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return -1, "", "timeout"
        return proc.returncode or 0, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")

    async def exec(self, cmd: str, *, timeout: float = 60.0, cwd: str | None = None, env: dict | None = None) -> ExecResult:
        start = time.monotonic()
        full = shlex.quote(cmd) if not cwd else f"cd {shlex.quote(cwd)} && {shlex.quote(cmd)}"
        argv = ["singularity", "exec"]
        for b in self.binds:
            argv += ["--bind", b]
        argv += [self.image, "sh", "-lc", full]
        rc, out, err = await self._run(argv, timeout=timeout)
        return ExecResult(ok=rc == 0, stdout=out, stderr=err, returncode=rc, elapsed_ms=int((time.monotonic() - start) * 1000))

    async def read(self, path: str) -> bytes:
        return Path(path).read_bytes()

    async def write(self, path: str, data: bytes) -> None:
        Path(path).write_bytes(data)

    async def sync_in(self, local: Path, remote: str) -> None:
        # Singularity binds local FS read-only by default; user supplies binds
        pass

    async def sync_out(self, remote: str, local: Path) -> None:
        local.parent.mkdir(parents=True, exist_ok=True)
        Path(local).write_bytes(Path(remote).read_bytes())

    async def close(self) -> None:
        pass
