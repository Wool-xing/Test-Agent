"""Local subprocess backend ()."""

from __future__ import annotations

import asyncio
import shlex
import shutil
import time
from pathlib import Path

from runtime.backends.base import BaseExecutionEnv, ExecResult, register


@register("local")
class LocalBackend(BaseExecutionEnv):
    async def connect(self) -> None:
        pass

    async def exec(self, cmd: str, *, timeout: float = 60.0, cwd: str | None = None, env: dict | None = None) -> ExecResult:
        start = time.monotonic()
        proc = await asyncio.create_subprocess_exec(
            *shlex.split(cmd), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd, env=env
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return ExecResult(ok=False, stdout="", stderr="timeout", returncode=None, elapsed_ms=int((time.monotonic() - start) * 1000))
        return ExecResult(
            ok=proc.returncode == 0,
            stdout=stdout.decode("utf-8", "replace"),
            stderr=stderr.decode("utf-8", "replace"),
            returncode=proc.returncode,
            elapsed_ms=int((time.monotonic() - start) * 1000),
        )

    async def read(self, path: str) -> bytes:
        return Path(path).read_bytes()

    async def write(self, path: str, data: bytes) -> None:
        Path(path).write_bytes(data)

    async def sync_in(self, local: Path, remote: str) -> None:
        # local==remote on local backend
        target = Path(remote)
        target.parent.mkdir(parents=True, exist_ok=True)
        if local.is_dir():
            shutil.copytree(local, target, dirs_exist_ok=True)
        else:
            shutil.copy2(local, target)

    async def sync_out(self, remote: str, local: Path) -> None:
        src = Path(remote)
        local.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, local, dirs_exist_ok=True)
        else:
            shutil.copy2(src, local)

    async def close(self) -> None:
        pass
