"""Scheduler tick loop.

- 60s tick from a background thread
- Cross-platform file lock (fcntl/msvcrt) prevents double-run
- Each due job: scan prompt -> route -> execute -> persist -> deliver
"""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from runtime.scheduler.injection_scan import PromptInjectionBlocked, scan
from runtime.scheduler.jobs import advance_job, due_jobs, output_dir

try:
    import fcntl

    _LOCK_BACKEND = "fcntl"
except ImportError:
    fcntl = None
    try:
        import msvcrt

        _LOCK_BACKEND = "msvcrt"
    except ImportError:
        msvcrt = None
        _LOCK_BACKEND = "noop"

_TICK_SECONDS = 60


def _acquire_lock(lock_path: Path):
    """Returns (file_handle, ok). ok=False means another tick is running."""
    f = open(lock_path, "a+")  # noqa: SIM115
    try:
        if _LOCK_BACKEND == "fcntl":
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        elif _LOCK_BACKEND == "msvcrt":
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        return f, True
    except OSError:
        f.close()
        return None, False


def _release_lock(f) -> None:
    try:
        if _LOCK_BACKEND == "fcntl":
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        elif _LOCK_BACKEND == "msvcrt":
            with contextlib.suppress(OSError):
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        with contextlib.suppress(OSError):
            f.close()


def _deliver_results(job: dict, result: dict) -> None:
    """Push job results to configured gateway platforms (async)."""
    delivery = job.get("delivery") or []
    if not delivery:
        return

    import asyncio

    async def _send():
        from runtime.gateway.base import Message, get_platform

        ok_str = "✅ OK" if result.get("ok") else "❌ Failed"
        text = (
            f"⏰ Scheduled task: {job.get('prompt', '')[:80]}\n"
            f"{ok_str}\n"
            f"Job: {job['id']}"
        )
        if result.get("output_path"):
            text += f"\nOutput: {result['output_path']}"

        for platform_name in delivery:
            try:
                p = get_platform(platform_name)
                await p.configure()
                msg = Message(text=text, user="test-agent")
                r = await p.send(msg)
                if not r.ok:
                    logger.warning("Job delivery failed via {}: {}", platform_name, r.error)
            except Exception as exc:
                logger.warning("Job delivery error for {}: {}", platform_name, exc)

    try:
        asyncio.run(_send())
    except Exception as exc:
        logger.warning("Job delivery async failed: {}", exc)


def run_job(job: dict, *, runner: Callable[[str], dict] | None = None) -> dict:
    """Execute a single job. `runner` defaults to runtime/api/deps.Kernel pipeline.

    Returns:
      dict: {"ok": bool, "run_id": str | None, "blocked": bool, "output_path": str}
    """
    job_id = job["id"]
    prompt = job.get("prompt", "")
    out_dir = output_dir(job_id)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_file = out_dir / f"{ts}.md"

    try:
        # runtime full-prompt injection scan
        scan(prompt)
    except PromptInjectionBlocked as e:
        out_file.write_text(f"# Job {job_id} blocked\n\nreason: {e.reason}\nsnippet: {e.snippet}\n", encoding="utf-8")
        advance_job(job_id, outcome="blocked", output_path=str(out_file))
        logger.warning("job {} blocked by injection scan: {}", job_id, e.reason)
        return {"ok": False, "run_id": None, "blocked": True, "output_path": str(out_file)}

    runner = runner or _default_runner
    try:
        result = runner(prompt)
        out_file.write_text(
            f"# Job {job_id} · {ts}\n\nprompt:\n{prompt}\n\nresult:\n{result}\n",
            encoding="utf-8",
        )
        advance_job(job_id, outcome="ok", output_path=str(out_file))
        ret = {"ok": True, "run_id": result.get("run_id") if isinstance(result, dict) else None, "blocked": False, "output_path": str(out_file)}
        _deliver_results(job, ret)
        return ret
    except Exception as e:
        out_file.write_text(f"# Job {job_id} failed\n\nerror: {e}\nprompt:\n{prompt}\n", encoding="utf-8")
        advance_job(job_id, outcome="failed", output_path=str(out_file))
        ret = {"ok": False, "run_id": None, "blocked": False, "output_path": str(out_file)}
        _deliver_results(job, ret)
        logger.exception("job {} failed", job_id)
        return ret


def _default_runner(prompt: str) -> dict:
    """Route via runtime/api/deps.Kernel."""
    from runtime.api.deps import Kernel
    from runtime.api.parsers import parse_text

    k = Kernel()
    art = parse_text(prompt)
    run_id, decision = k.submit(art, persist=False)
    summary = k.execute_sync(run_id, decision)
    return {"run_id": run_id, "summary": summary}


def tick() -> int:
    """Run one tick. Returns number of jobs processed."""
    from runtime.config.settings import get_settings

    s = get_settings()
    lock_path = s.resolve(s.workspace_dir) / "cron" / ".tick.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    fh, ok = _acquire_lock(lock_path)
    if not ok:
        logger.debug("tick already running, skipping")
        return 0
    try:
        jobs = due_jobs()
        for j in jobs:
            run_job(j)
        return len(jobs)
    finally:
        _release_lock(fh)


def run_forever(interval: int = _TICK_SECONDS, stop: threading.Event | None = None) -> None:
    """Foreground loop; for production use a background thread."""
    stop = stop or threading.Event()
    while not stop.is_set():
        try:
            tick()
        except Exception:
            logger.exception("tick crashed")
        stop.wait(interval)


def start_background(interval: int = _TICK_SECONDS) -> tuple[threading.Thread, threading.Event]:
    """Start scheduler in a daemon thread; returns (thread, stop_event)."""
    stop = threading.Event()
    t = threading.Thread(target=run_forever, args=(interval, stop), daemon=True, name="tagent-scheduler")
    t.start()
    return t, stop
