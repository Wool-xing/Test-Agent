"""Daytona dev sandbox backend (serverless hibernate)."""

from __future__ import annotations

import shlex
import time
from pathlib import Path

from runtime.backends.base import BaseExecutionEnv, ExecResult, register


@register("daytona")
class DaytonaBackend(BaseExecutionEnv):
    """Wrap a Daytona workspace via its CLI (`daytona`).

    Requires the Daytona CLI on PATH + authenticated profile.
    workspace hibernates when idle, wakes on demand.
    """

    def __init__(self, workspace: str, *, profile: str | None = None) -> None:
        self.workspace = workspace
        self.profile = profile

    async def connect(self) -> None:
        # Daytona CLI uses ambient auth; nothing to do at connect time
        pass

    async def _cli(self, argv: list[str], *, timeout: float = 120.0) -> tuple[int, str, str]:
        import asyncio

        prefix = ["daytona"]
        if self.profile:
            prefix += ["--profile", self.profile]
        proc = await asyncio.create_subprocess_exec(*prefix, *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return -1, "", "timeout"
        rc = proc.returncode if proc.returncode is not None else -1
        return rc, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")

    async def exec(self, cmd: str, *, timeout: float = 60.0, cwd: str | None = None, env: dict | None = None) -> ExecResult:
        start = time.monotonic()
        full = shlex.quote(cmd)
        if cwd:
            full = f"cd {shlex.quote(cwd)} && {full}"
        rc, out, err = await self._cli(["ssh", self.workspace, "--", "sh", "-lc", full], timeout=timeout)
        return ExecResult(ok=rc == 0, stdout=out, stderr=err, returncode=rc, elapsed_ms=int((time.monotonic() - start) * 1000))

    async def read(self, path: str) -> bytes:
        rc, out, _ = await self._cli(["ssh", self.workspace, "--", "cat", path])
        if rc != 0:
            raise FileNotFoundError(path)
        return out.encode("utf-8")

    async def write(self, path: str, data: bytes) -> None:
        # encode then heredoc; for binary safe transfer use sync_in
        import base64

        b64 = base64.b64encode(data).decode("ascii")
        await self._cli(["ssh", self.workspace, "--", "sh", "-lc", f"echo {b64} | base64 -d > {shlex.quote(path)}"])

    async def sync_in(self, local: Path, remote: str) -> None:
        await self._cli(["cp", str(local), f"{self.workspace}:{remote}"])

    async def sync_out(self, remote: str, local: Path) -> None:
        local.parent.mkdir(parents=True, exist_ok=True)
        await self._cli(["cp", f"{self.workspace}:{remote}", str(local)])

    async def close(self) -> None:
        pass
