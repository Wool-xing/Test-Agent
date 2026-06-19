"""Test ExecutionContext: thread safety, degraded detection, basic flow."""

from __future__ import annotations

import threading

from runtime.orchestrator.context import ExecutionContext


def test_basic_set_get():
    """Set and get output + meta on a single context."""
    ctx = ExecutionContext(run_id="test-basic")
    ctx.set_output("node-a", {"x": 1}, {"degraded": False, "ok": True})
    assert ctx.get_output("node-a") == {"x": 1}
    assert ctx.get_meta("node-a") == {"degraded": False, "ok": True}
    assert ctx.get_output("nonexistent") is None
    assert ctx.get_meta("nonexistent") is None


def test_is_degraded():
    """Degraded flag detection."""
    ctx = ExecutionContext(run_id="test-degraded")
    ctx.set_output("ok-node", {"v": 0}, {"degraded": False})
    ctx.set_output("bad-node", {"v": 1}, {"degraded": True})
    ctx.set_output("no-meta", {"v": 2})
    assert not ctx.is_degraded("ok-node")
    assert ctx.is_degraded("bad-node")
    assert not ctx.is_degraded("no-meta")
    assert not ctx.is_degraded("nonexistent")


def test_has_any_degraded():
    """Aggregate degraded check across all nodes."""
    ctx = ExecutionContext(run_id="test-any-degraded")
    assert not ctx.has_any_degraded()
    ctx.set_output("a", {}, {"degraded": False})
    assert not ctx.has_any_degraded()
    ctx.set_output("b", {}, {"degraded": True})
    assert ctx.has_any_degraded()


def test_snapshot_consistency():
    """Snapshot returns a consistent copy of current state."""
    ctx = ExecutionContext(run_id="test-snapshot")
    ctx.set_output("a", {"v": 1}, {"ok": True})
    ctx.set_output("b", {"v": 2}, {"ok": False, "degraded": True})
    outputs, meta = ctx.snapshot()
    assert outputs == {"a": {"v": 1}, "b": {"v": 2}}
    assert meta == {"a": {"ok": True}, "b": {"ok": False, "degraded": True}}
    # Snapshot is a copy — mutating it does not affect the context
    outputs["c"] = {"v": 3}
    assert ctx.get_output("c") is None


def test_thread_safety():
    """Multi-threaded set/get does not corrupt state."""
    ctx = ExecutionContext(run_id="test-threads")
    errors: list[str] = []
    barrier = threading.Barrier(4)

    def worker(prefix: str, count: int):
        try:
            barrier.wait()
            for i in range(count):
                nid = f"{prefix}-{i}"
                ctx.set_output(nid, {"val": i}, {"degraded": i % 3 == 0})
                out = ctx.get_output(nid)
                if out != {"val": i}:
                    errors.append(f"{nid}: expected {{'val': {i}}}, got {out}")
        except Exception as exc:
            errors.append(f"{prefix} crashed: {exc}")

    threads = [
        threading.Thread(target=worker, args=("w0", 50)),
        threading.Thread(target=worker, args=("w1", 50)),
        threading.Thread(target=worker, args=("w2", 50)),
        threading.Thread(target=worker, args=("w3", 50)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"thread-safety errors: {errors}"
    # Each worker wrote 50 entries, 4 workers = 200 total
    assert len(ctx.upstream_outputs) == 200
    assert len(ctx.upstream_meta) == 200
