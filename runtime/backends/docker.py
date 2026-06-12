"""Docker backend (hermes ). Wraps `docker exec` for a named container."""

from __future__ import annotations

import asyncio
import shlex
import time
from pathlib import Path

from runtime.backends.base import BaseExecutionEnv, ExecResult, register


@register("docker")
class DockerBackend(BaseExecutionEnv):
    def __init__(self, container: str, *, image: str | None = None) -> None:
        self.container = container
        self.image = image

    async def connect(self) -> None:
        if self.image:
            await self._run(["docker", "pull", self.image])
            await self._run(["docker", "run", "-d", "--name", self.container, self.image, "sleep", "infinity"])

    async def _run(self, argv: list[str], *, timeout: float = 120.0) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return -1, "", "timeout"
        rc = proc.returncode if proc.returncode is not None else -1
        return rc, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")

    async def exec(self, cmd: str, *, timeout: float = 60.0, cwd: str | None = None, env: dict | None = None) -> ExecResult:
        start = time.monotonic()
        argv = ["docker", "exec"]
        if cwd:
            argv += ["-w", cwd]
        for k, v in (env or {}).items():
            argv += ["-e", f"{k}={v}"]
        argv += [self.container, "sh", "-lc", shlex.quote(cmd)]
        rc, out, err = await self._run(argv, timeout=timeout)
        return ExecResult(ok=rc == 0, stdout=out, stderr=err, returncode=rc, elapsed_ms=int((time.monotonic() - start) * 1000))

    async def read(self, path: str) -> bytes:
        rc, out, _ = await self._run(["docker", "exec", self.container, "cat", path])
        if rc != 0:
            raise FileNotFoundError(path)
        return out.encode("utf-8")

    async def write(self, path: str, data: bytes) -> None:
        # `docker cp` from stdin requires temp file
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name
        try:
            await self._run(["docker", "cp", tmp_path, f"{self.container}:{path}"])
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def sync_in(self, local: Path, remote: str) -> None:
        await self._run(["docker", "cp", str(local), f"{self.container}:{remote}"])

    async def sync_out(self, remote: str, local: Path) -> None:
        local.parent.mkdir(parents=True, exist_ok=True)
        await self._run(["docker", "cp", f"{self.container}:{remote}", str(local)])

    async def close(self) -> None:
        # don't auto-rm; user controls container lifecycle
        pass
