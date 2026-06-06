"""Vercel Sandbox backend (hermes §1.4 边缘运行)."""

from __future__ import annotations

import contextlib
import time
from pathlib import Path

from loguru import logger

from runtime.backends.base import BaseExecutionEnv, ExecResult, register


@register("vercel_sandbox")
class VercelSandboxBackend(BaseExecutionEnv):
    """Wrap a Vercel Sandbox via its HTTP API.

    Requires VERCEL_TOKEN env var. Sandbox spawns at edge nodes.
    """

    def __init__(self, project_id: str, *, region: str = "iad1") -> None:
        self.project_id = project_id
        self.region = region
        self._sandbox_id: str | None = None
        self._client = None

    async def connect(self) -> None:
        import os

        try:
            import httpx
        except ImportError as e:
            raise RuntimeError("httpx not installed") from e
        token = os.getenv("VERCEL_TOKEN")
        if not token:
            raise RuntimeError("VERCEL_TOKEN env not set")
        # Close previous client to avoid connection pool leak on reconnect
        if self._client is not None:
            with contextlib.suppress(Exception):
                await self._client.aclose()
        self._client = httpx.AsyncClient(
            base_url="https://api.vercel.com",
            headers={"Authorization": f"Bearer {token}"},
            timeout=60.0,
        )
        resp = await self._client.post(
            "/v1/sandboxes",
            json={"projectId": self.project_id, "region": self.region},
        )
        resp.raise_for_status()
        self._sandbox_id = resp.json().get("id")
        logger.info("Vercel Sandbox created: {}", self._sandbox_id)

    async def exec(self, cmd: str, *, timeout: float = 60.0, cwd: str | None = None, env: dict | None = None) -> ExecResult:
        start = time.monotonic()
        if self._sandbox_id is None or self._client is None:
            return ExecResult(ok=False, stdout="", stderr="not connected", returncode=None, elapsed_ms=0)
        body = {"command": cmd, "cwd": cwd, "env": env or {}, "timeout_ms": int(timeout * 1000)}
        try:
            resp = await self._client.post(f"/v1/sandboxes/{self._sandbox_id}/exec", json=body)
            resp.raise_for_status()
            data = resp.json()
            return ExecResult(
                ok=data.get("exitCode") == 0,
                stdout=data.get("stdout", ""),
                stderr=data.get("stderr", ""),
                returncode=data.get("exitCode"),
                elapsed_ms=int((time.monotonic() - start) * 1000),
            )
        except Exception as e:
            return ExecResult(ok=False, stdout="", stderr=str(e), returncode=None, elapsed_ms=int((time.monotonic() - start) * 1000))

    async def read(self, path: str) -> bytes:
        resp = await self._client.get(f"/v1/sandboxes/{self._sandbox_id}/files", params={"path": path})
        resp.raise_for_status()
        return resp.content

    async def write(self, path: str, data: bytes) -> None:
        await self._client.put(f"/v1/sandboxes/{self._sandbox_id}/files", params={"path": path}, content=data)

    async def sync_in(self, local: Path, remote: str) -> None:
        await self.write(remote, local.read_bytes() if local.is_file() else b"")

    async def sync_out(self, remote: str, local: Path) -> None:
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(await self.read(remote))

    async def close(self) -> None:
        if self._client and self._sandbox_id:
            with contextlib.suppress(Exception):
                await self._client.delete(f"/v1/sandboxes/{self._sandbox_id}")
        if self._client:
            await self._client.aclose()
        self._client = None
        self._sandbox_id = None
