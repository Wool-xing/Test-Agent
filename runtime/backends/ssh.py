"""SSH backend (hermes §1.4). Uses asyncssh for persistent connection."""

from __future__ import annotations

import shlex
import time
from pathlib import Path

from loguru import logger

from runtime.backends.base import BaseExecutionEnv, ExecResult, register


@register("ssh")
class SSHBackend(BaseExecutionEnv):
    def __init__(self, host: str, *, user: str = "root", port: int = 22, key: str | None = None, password: str | None = None) -> None:
        self.host = host
        self.user = user
        self.port = port
        self.key = key
        self.password = password
        self._conn = None

    async def connect(self) -> None:
        try:
            import asyncssh  # type: ignore
        except ImportError as e:
            raise RuntimeError("asyncssh not installed; pip install asyncssh") from e
        self._conn = await asyncssh.connect(
            self.host, port=self.port, username=self.user, client_keys=[self.key] if self.key else None, password=self.password, known_hosts=None
        )
        logger.info("SSH connected: {}@{}:{}", self.user, self.host, self.port)

    async def exec(self, cmd: str, *, timeout: float = 60.0, cwd: str | None = None, env: dict | None = None) -> ExecResult:
        start = time.monotonic()
        full = cmd
        if cwd:
            full = f"cd {shlex.quote(cwd)} && {shlex.quote(cmd)}"
        if env:
            env_str = " ".join(f"{shlex.quote(k)}={shlex.quote(v)}" for k, v in env.items())
            full = f"{env_str} {full}"
        try:
            result = await self._conn.run(full, check=False, timeout=timeout)
            return ExecResult(
                ok=result.exit_status == 0,
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                returncode=result.exit_status,
                elapsed_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as e:
            return ExecResult(ok=False, stdout="", stderr=str(e), returncode=None, elapsed_ms=int((time.monotonic() - start) * 1000))

    async def read(self, path: str) -> bytes:
        async with self._conn.start_sftp_client() as sftp, sftp.open(path, "rb") as f:
            return await f.read()

    async def write(self, path: str, data: bytes) -> None:
        async with self._conn.start_sftp_client() as sftp, sftp.open(path, "wb") as f:
            await f.write(data)

    async def sync_in(self, local: Path, remote: str) -> None:
        async with self._conn.start_sftp_client() as sftp:
            await sftp.put(str(local), remote, recurse=local.is_dir())

    async def sync_out(self, remote: str, local: Path) -> None:
        local.parent.mkdir(parents=True, exist_ok=True)
        async with self._conn.start_sftp_client() as sftp:
            await sftp.get(remote, str(local), recurse=True)

    async def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
