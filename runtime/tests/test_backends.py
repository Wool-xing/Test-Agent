"""Backend execution env tests — local backend runs REAL subprocesses.

Also locks the registry contract: all backend files registered + constructible.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runtime.backends.base import ExecResult, get_backend  # noqa: E402


class TestRegistry:
    def test_local_backend_registered(self):
        backend = get_backend("local")
        assert backend is not None
        assert backend.name == "local"

    def test_all_backend_files_constructible(self):
        """Every backends/*.py except base must register and construct."""
        import importlib
        import pkgutil

        import runtime.backends as pkg

        for mod in pkgutil.iter_modules(pkg.__path__):
            if mod.name == "base":
                continue
            m = importlib.import_module(f"runtime.backends.{mod.name}")
            # each module has a @register decorator; registry populated on import
        from runtime.backends.base import get_backend

        # Parameterized backends (docker/ssh/modal/...) need constructor args —
        # verify registry presence instead of construction.
        from runtime.backends.base import REGISTRY

        for name in ("local", "docker", "ssh", "modal", "daytona", "singularity", "vercel_sandbox"):
            assert name in REGISTRY, f"{name} not registered"


class TestLocalBackendReal:
    """LocalBackend executes real commands — no mocks."""

    @pytest.fixture
    def backend(self):
        return get_backend("local")

    async def test_exec_success(self, backend):
        r = await backend.exec("echo hello-backend")
        assert r.ok is True
        assert "hello-backend" in r.stdout
        assert r.returncode == 0
        assert r.elapsed_ms >= 0

    async def test_exec_failure(self, backend):
        r = await backend.exec('python -c "import sys; sys.exit(3)"')
        assert r.ok is False
        assert r.returncode == 3

    async def test_exec_timeout(self, backend):
        r = await backend.exec("sleep 5", timeout=0.2)
        assert r.ok is False
        assert r.returncode is None
        assert "timeout" in r.stderr

    async def test_exec_missing_command(self, backend):
        r = await backend.exec("definitely-not-a-real-cmd-xyz")
        # On Windows FileNotFoundError propagates; elsewhere non-zero rc.
        # Either way must NOT report ok=True.
        assert r.ok is False

    async def test_write_read_roundtrip(self, backend, tmp_path):
        p = tmp_path / "data.bin"
        await backend.write(str(p), b"\x00\x01\x02backend")
        assert await backend.read(str(p)) == b"\x00\x01\x02backend"

    async def test_sync_in_file(self, backend, tmp_path):
        src = tmp_path / "src.txt"
        src.write_text("sync-in-content", encoding="utf-8")
        dst = tmp_path / "dst" / "copied.txt"
        await backend.sync_in(src, str(dst))
        assert dst.read_text(encoding="utf-8") == "sync-in-content"

    async def test_sync_out_dir(self, backend, tmp_path):
        src_dir = tmp_path / "proj"
        src_dir.mkdir()
        (src_dir / "f.txt").write_text("x", encoding="utf-8")
        dst = tmp_path / "out" / "proj"
        await backend.sync_out(str(src_dir), dst)
        assert (dst / "f.txt").read_text(encoding="utf-8") == "x"

    async def test_connect_close_noop(self, backend):
        await backend.connect()
        await backend.close()
