"""Singularity / Apptainer backend (hermes ; HPC-friendly)."""

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
        rc = proc.returncode if proc.returncode is not None else -1
        return rc, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")

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
        """Read file from inside the container (like docker exec cat)."""
        argv = ["singularity", "exec"]
        for b in self.binds:
            argv += ["--bind", b]
        argv += [self.image, "cat", path]
        rc, out, err = await self._run(argv)
        if rc != 0:
            raise FileNotFoundError(f"container:{path} ({err[:200]})")
        return out.encode("utf-8")

    async def write(self, path: str, data: bytes) -> None:
        """Write file into the container via base64 pipe (no docker cp equivalent)."""
        import base64
        b64 = base64.b64encode(data).decode("ascii")
        argv = ["singularity", "exec"]
        for b in self.binds:
            argv += ["--bind", b]
        argv += [self.image, "sh", "-lc", f"echo {b64} | base64 -d > {shlex.quote(path)}"]
        rc, _, err = await self._run(argv)
        if rc != 0:
            raise OSError(f"container write failed: {path} ({err[:200]})")

    async def sync_in(self, local: Path, remote: str) -> None:
        """Copy local host file into the container."""
        await self.write(remote, local.read_bytes())

    async def sync_out(self, remote: str, local: Path) -> None:
        """Copy file from container to local host."""
        data = await self.read(remote)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(data)

    async def close(self) -> None:
        pass
