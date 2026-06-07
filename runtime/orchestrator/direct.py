"""Prefect-less direct executor.

Supports hard/soft dependencies:
  - hard (default): upstream failure blocks downstream (data integrity)
  - soft: upstream failure tolerated, downstream runs with integrity=degraded

Parallel execution: independent branches run concurrently via ThreadPoolExecutor.
Circuit breaker: ≥3 failures aborts remaining nodes.
"""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from runtime.observability.logging import bind_run, configure_logging
from runtime.observability.otel import init_tracing, span
from runtime.orchestrator.adapters.experts import execute_node, reset_upstream_cache
from runtime.router.schema import DAGNode, RoutingDecision
from runtime.self_healing.retry import with_retry


def _is_abort_exception(exc: Exception) -> bool:
    """Check if exception signals an on_failure=abort (not a transient error)."""
    return isinstance(exc, RuntimeError) and "aborted" in str(exc)


def _is_hard(node: DAGNode) -> bool:
    """Check if this node requires all upstream to succeed."""
    return getattr(node, "dep_mode", "hard") == "hard"


def _run_node_with_retry(node: DAGNode, results: dict, log) -> None:
    """Execute a node with retries, respecting on_failure policy.

    on_failure modes:
      - retry (default): retry 2x with exp backoff, mark failed after
      - skip: mark skipped on first failure, don't retry, don't block
      - abort: stop entire DAG immediately
    """
    nid = node.id
    try:
        results[nid] = _run_node(node)
    except Exception as exc:
        log.warning("node {} attempt failed: {}", nid, exc)
        if node.on_failure == "skip":
            results[nid] = {"id": nid, "ok": False, "skipped": True, "error": str(exc)}
            return
        if node.on_failure == "abort" or _is_abort_exception(exc):
            results[nid] = {"id": nid, "ok": False, "error": str(exc), "aborted": True}
            return
        # retry up to 2 more times for transient errors
        for attempt in range(2):
            time.sleep(2 ** attempt)
            try:
                results[nid] = _run_node(node)
                return
            except Exception as retry_exc:
                log.warning("node {} retry {}/2 failed", nid, attempt + 1)
                if node.on_failure == "abort" or _is_abort_exception(retry_exc):
                    results[nid] = {"id": nid, "ok": False, "error": str(retry_exc), "aborted": True}
                    return
                if attempt == 1:
                    results[nid] = {"id": nid, "ok": False, "error": str(retry_exc)}


def _run_node(node: DAGNode) -> dict[str, Any]:
    from runtime.orchestrator.hooks import get_hook_registry

    hooks = get_hook_registry()
    ctx = {"name": node.name, "kind": node.kind, "inputs": node.inputs, "timeout": node.timeout_seconds}
    hooks.fire_before(node.id, ctx)

    try:
        with span(f"node.{node.kind}.{node.name}", node_id=node.id):

            def _execute() -> Any:
                return execute_node(name=node.name, kind=node.kind, inputs=node.inputs, timeout=node.timeout_seconds)

            outcome = with_retry(_execute)()
        summary = {
            "id": node.id,
            "name": outcome.name,
            "kind": outcome.kind,
            "executed_script": outcome.executed_script,
            "returncode": outcome.returncode,
            "duration_ms": outcome.duration_ms,
            "ok": outcome.ok,
            "stdout_tail": outcome.stdout[-2000:] if outcome.stdout else "",
            "stderr_tail": outcome.stderr[-2000:] if outcome.stderr else "",
        }
        ctx["results"] = summary
        hooks.fire_after(node.id, ctx)
        if not outcome.ok and node.on_failure == "abort":
            raise RuntimeError(f"node {node.id} aborted: rc={outcome.returncode}")
    except Exception as exc:
        ctx["error"] = str(exc)
        hooks.fire_error(node.id, ctx)
        raise
    return summary


def _notify(on_progress: Any, result: dict | None) -> None:
    """Fire on_progress callback if set and result is truthy."""
    if on_progress and result:
        on_progress(result)


def run_decision_direct(decision_dict: dict[str, Any], run_id: str, max_workers: int = 4, on_progress: Any = None) -> dict[str, Any]:
    if on_progress is not None and not callable(on_progress):
        on_progress = None
    configure_logging()
    init_tracing()
    log = bind_run(run_id)
    reset_upstream_cache()  # V1.14 主宪章 §40
    decision = RoutingDecision.model_validate(decision_dict)
    ordered: list[DAGNode] = decision.topological()
    log.info("direct flow start: run_id={} nodes={}", run_id, len(ordered))

    MAX_FAILURES = 3
    by_id: dict[str, DAGNode] = {n.id: n for n in ordered}
    results: dict[str, dict] = {}
    failures: list[str] = []
    skipped: list[str] = []
    pending = set(by_id.keys())
    futures: dict[str, Future] = {}
    circuit_broken = False
    pool = None
    try:
        pool = ThreadPoolExecutor(max_workers=max_workers)
        with span("flow.run", run_id=run_id, nodes=len(ordered)):
            while pending:
                # circuit breaker: stop submitting new work
                if circuit_broken:
                    # drain in-flight futures
                    for nid in list(pending):
                        if nid in futures:
                            try:
                                results[nid] = futures[nid].result()
                            except Exception:
                                results[nid] = {"id": nid, "ok": False, "error": "circuit broken"}
                            pending.discard(nid)
                            _notify(on_progress, results.get(nid))
                    break
                # find nodes whose deps are satisfied:
                #   hard deps must ALL be OK (upstream failure → block)
                #   soft deps just need a result (upstream failure → tolerated, run degraded)
                ready = []
                for nid in list(pending):
                    if nid in futures:
                        continue
                    node = by_id[nid]
                    all_deps = node.depends_on
                    hard_deps = all_deps if _is_hard(node) else []
                    # All hard deps succeeded, all deps have results
                    if all(d in results and results[d].get("ok", False) for d in hard_deps) and \
                       all(d in results for d in all_deps):
                        # If any soft dep failed, inject partial flag
                        soft_failed = [d for d in all_deps if d not in hard_deps
                                       and d in results and not results[d].get("ok", False)]
                        if soft_failed:
                            node.inputs["integrity"] = "partial"
                            node.inputs["degraded_by"] = soft_failed
                        ready.append(nid)
                for nid in ready:
                    futures[nid] = pool.submit(_run_node, by_id[nid])
                # wait for at least one to finish
                done_now = [nid for nid, f in futures.items() if f.done() and nid in pending]
                if not done_now:
                    # block on the oldest pending future
                    next_id = next(nid for nid in futures if nid in pending)
                    try:
                        results[next_id] = futures[next_id].result()
                    except Exception as exc:
                        log.warning("node {} attempt failed: {}", next_id, exc)
                        _run_node_with_retry(by_id[next_id], results, log)
                    r = results.get(next_id)
                    if r:
                        if r.get("skipped"):
                            skipped.append(next_id)
                        elif not r.get("ok"):
                            failures.append(next_id)
                            if r.get("aborted") or len(failures) >= MAX_FAILURES:
                                if r.get("aborted"):
                                    log.error("node {} aborted, terminating DAG", next_id)
                                else:
                                    log.error("circuit breaker: {} failures, aborting DAG", len(failures))
                                circuit_broken = True
                    pending.discard(next_id)
                    _notify(on_progress, r)
                    continue
                for nid in done_now:
                    try:
                        results[nid] = futures[nid].result()
                    except Exception as exc:
                        results[nid] = {"id": nid, "ok": False, "error": str(exc), "aborted": _is_abort_exception(exc)}
                    r = results.get(nid)
                    if r:
                        if r.get("skipped"):
                            skipped.append(nid)
                        elif not r.get("ok"):
                            failures.append(nid)
                            if r.get("aborted") or len(failures) >= MAX_FAILURES:
                                if r.get("aborted"):
                                    log.error("node {} aborted, terminating DAG", nid)
                                else:
                                    log.error("circuit breaker: {} failures, aborting DAG", len(failures))
                                circuit_broken = True
                    pending.discard(nid)
                    _notify(on_progress, r)
                    # After processing results, skip nodes whose HARD deps failed
                    unreachable = [
                        nid for nid in list(pending)
                        if nid not in futures
                        and all(d in results for d in by_id[nid].depends_on)  # all deps resolved
                        and not all(d in results and results[d].get("ok", False)
                                    for d in by_id[nid].depends_on
                                    if _is_hard(by_id[nid]))  # hard dep failed → unreachable
                    ]
                    for nid in unreachable:
                        failed_upstream = [d for d in by_id[nid].depends_on
                                          if d in results and not results[d].get("ok", False)]
                        results[nid] = {
                            "id": nid, "ok": False, "skipped": True,
                            "error": f"skipped: upstream failed ({', '.join(failed_upstream[:3])})"
                        }
                        skipped.append(nid)
                        pending.discard(nid)
    finally:
        if pool is not None:
            pool.shutdown(wait=True)

    completed = len(results)
    log.info("DAG progress: {}/{} nodes done, {} failed, {} skipped", completed, len(ordered), len(failures), len(skipped))

    # L2-C: rollout 节点 + on_failure=skip 节点
    rollout_skipped = [
        nid for nid, r in results.items()
        if not r.get("ok") and "[V1.x rollout]" in (r.get("stderr_tail") or "")
    ] + skipped

    summary = {
        "run_id": run_id,
        "total": len(ordered),
        "succeeded": len(ordered) - len(failures) - len(skipped),
        "failed": len(failures),
        "skipped": len(skipped),
        "rollout_skipped": rollout_skipped,
        "results": results,
    }
    log.info(
        "direct flow done: {}/{} ok, {} failed, {} skipped",
        summary["succeeded"], summary["total"], summary["failed"], summary["skipped"]
    )
    return summary
