"""Modal serverless backend (hermes §1.4 经济模型 — hibernate when idle).

Modal client SDK must be installed and authenticated:
    pip install modal
    modal token new
"""

from __future__ import annotations

import time
from pathlib import Path

from loguru import logger

from runtime.backends.base import BaseExecutionEnv, ExecResult, register


@register("modal")
class ModalBackend(BaseExecutionEnv):
    """Wrap a Modal Function/App; commands run inside a hibernated container.

    Hermes §1.4 经济模型: ground-state nearly zero cost when idle.
    """

    def __init__(self, app_name: str, *, image: str | None = None) -> None:
        self.app_name = app_name
        self.image = image
        self._sandbox = None

    async def connect(self) -> None:
        try:
            import modal  # type: ignore
        except ImportError as e:
            raise RuntimeError("modal not installed; pip install modal") from e
        # Sandbox API allows arbitrary exec inside an isolated container
        try:
            app = modal.App.lookup(self.app_name, create_if_missing=True)
            image = modal.Image.debian_slim() if not self.image else modal.Image.from_registry(self.image)
            self._sandbox = modal.Sandbox.create(app=app, image=image)
            logger.info("Modal sandbox created: {}", self.app_name)
        except Exception as e:
            raise RuntimeError(f"Modal sandbox creation failed: {e}") from e

    async def exec(self, cmd: str, *, timeout: float = 60.0, cwd: str | None = None, env: dict | None = None) -> ExecResult:
        start = time.monotonic()
        if self._sandbox is None:
            return ExecResult(ok=False, stdout="", stderr="not connected", returncode=None, elapsed_ms=0)
        try:
            full = cmd if not cwd else f"cd {cwd} && {cmd}"
            proc = self._sandbox.exec("sh", "-lc", full)
            stdout = proc.stdout.read()
            stderr = proc.stderr.read()
            rc = proc.wait()
            return ExecResult(ok=rc == 0, stdout=stdout, stderr=stderr, returncode=rc, elapsed_ms=int((time.monotonic() - start) * 1000))
        except Exception as e:
            return ExecResult(ok=False, stdout="", stderr=str(e), returncode=None, elapsed_ms=int((time.monotonic() - start) * 1000))

    async def read(self, path: str) -> bytes:
        if self._sandbox is None:
            raise RuntimeError("not connected")
        with self._sandbox.open(path, "rb") as f:
            return f.read()

    async def write(self, path: str, data: bytes) -> None:
        if self._sandbox is None:
            raise RuntimeError("not connected")
        with self._sandbox.open(path, "wb") as f:
            f.write(data)

    async def sync_in(self, local: Path, remote: str) -> None:
        await self.write(remote, local.read_bytes() if local.is_file() else b"")

    async def sync_out(self, remote: str, local: Path) -> None:
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(await self.read(remote))

    async def close(self) -> None:
        if self._sandbox is not None:
            self._sandbox.terminate()
            self._sandbox = None
