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
from runtime.orchestrator.context import ExecutionContext
from runtime.router.schema import DAGNode, RoutingDecision
from runtime.self_healing.retry import with_retry


def _is_abort_exception(exc: Exception) -> bool:
    """Check if exception signals an on_failure=abort (not a transient error)."""
    return isinstance(exc, RuntimeError) and "aborted" in str(exc)


def _is_hard(node: DAGNode) -> bool:
    """Check if this node requires all upstream to succeed."""
    return getattr(node, "dep_mode", "hard") == "hard"


def _run_node_with_retry(node: DAGNode, results: dict, log, ctx: ExecutionContext) -> None:
    """Execute a node with retries, respecting on_failure policy.

    on_failure modes:
      - retry (default): retry 2x with exp backoff, mark failed after
      - skip: mark skipped on first failure, don't retry, don't block
      - abort: stop entire DAG immediately
    """
    nid = node.id
    try:
        results[nid] = _run_node(node, ctx)
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
                results[nid] = _run_node(node, ctx)
                return
            except Exception as retry_exc:
                log.warning("node {} retry {}/2 failed", nid, attempt + 1)
                if node.on_failure == "abort" or _is_abort_exception(retry_exc):
                    results[nid] = {"id": nid, "ok": False, "error": str(retry_exc), "aborted": True}
                    return
                if attempt == 1:
                    results[nid] = {"id": nid, "ok": False, "error": str(retry_exc)}


def _run_node(node: DAGNode, exec_ctx: ExecutionContext) -> dict[str, Any]:
    from runtime.orchestrator.hooks import get_hook_registry

    hooks = get_hook_registry()
    hook_ctx = {"name": node.name, "kind": node.kind, "inputs": node.inputs, "timeout": node.timeout_seconds}
    hooks.fire_before(node.id, hook_ctx)

    try:
        with span(f"node.{node.kind}.{node.name}", node_id=node.id):

            def _execute() -> Any:
                return execute_node(
                    name=node.name,
                    kind=node.kind,
                    inputs=node.inputs,
                    timeout=node.timeout_seconds,
                    ctx=exec_ctx,
                )

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
        hook_ctx["results"] = summary
        hooks.fire_after(node.id, hook_ctx)
        if not outcome.ok and node.on_failure == "abort":
            raise RuntimeError(f"node {node.id} aborted: rc={outcome.returncode}")
    except Exception as exc:
        hook_ctx["error"] = str(exc)
        hooks.fire_error(node.id, hook_ctx)
        raise
    return summary


def _notify(on_progress: Any, result: dict | None) -> None:
    """Fire on_progress callback if set and result is truthy."""
    if on_progress and result:
        on_progress(result)


def _classify_result(nid: str, r: dict | None, failures: list[str], skipped: list[str],
                    MAX_FAILURES: int) -> bool:
    """Classify a completed node result. Returns True if circuit breaker triggered."""
    if not r:
        return False
    if r.get("skipped"):
        skipped.append(nid)
    elif not r.get("ok"):
        failures.append(nid)
        if r.get("aborted") or len(failures) >= MAX_FAILURES:
            return True
    return False


def _mark_unreachable(pending: set[str], results: dict, by_id: dict, skipped: list[str],
                      futures: dict) -> None:
    """Skip nodes whose hard deps failed (unreachable after upstream failure)."""
    unreachable = [
        nid for nid in list(pending)
        if nid not in futures
        and all(d in results for d in by_id[nid].depends_on)
        and not all(d in results and results[d].get("ok", False)
                    for d in by_id[nid].depends_on
                    if _is_hard(by_id[nid]))
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


def _find_ready_nodes(pending: set, futures: dict, by_id: dict, results: dict) -> list[str]:
    """Find nodes whose dependencies are all satisfied."""
    ready = []
    for nid in list(pending):
        if nid in futures:
            continue
        node = by_id[nid]
        all_deps = node.depends_on
        hard_deps = all_deps if _is_hard(node) else []
        if all(d in results and results[d].get("ok", False) for d in hard_deps) and \
           all(d in results for d in all_deps):
            soft_failed = [d for d in all_deps if d not in hard_deps
                           and d in results and not results[d].get("ok", False)]
            if soft_failed:
                node.inputs["integrity"] = "partial"
                node.inputs["degraded_by"] = soft_failed
            ready.append(nid)
    return ready


def _drain_inflight(pending: set, futures: dict, results: dict, on_progress) -> None:
    """Collect results from all in-flight futures after circuit breaker trips."""
    for nid in list(pending):
        if nid in futures:
            try:
                results[nid] = futures[nid].result()
            except Exception:
                results[nid] = {"id": nid, "ok": False, "error": "circuit broken"}
            pending.discard(nid)
            _notify(on_progress, results.get(nid))


def _process_batch_results(done_now: list[str], futures: dict, results: dict,
                           by_id: dict, pending: set, failures: list[str],
                           skipped: list[str], on_progress) -> bool:
    """Process a batch of completed nodes. Returns True if circuit breaker triggered."""
    circuit_broken = False
    for nid in done_now:
        try:
            results[nid] = futures[nid].result()
        except Exception as exc:
            results[nid] = {"id": nid, "ok": False, "error": str(exc), "aborted": _is_abort_exception(exc)}
        r = results.get(nid)
        if _classify_result(nid, r, failures, skipped, MAX_FAILURES=3):
            circuit_broken = True
        pending.discard(nid)
        _notify(on_progress, r)
        _mark_unreachable(pending, results, by_id, skipped, futures)
    return circuit_broken


def _block_on_oldest(futures: dict, pending: set, by_id: dict, results: dict,
                     exec_ctx: ExecutionContext, log) -> dict | None:
    """Block on the oldest pending future, with retry on failure."""
    next_id = next(nid for nid in futures if nid in pending)
    try:
        results[next_id] = futures[next_id].result()
    except Exception as exc:
        log.warning("node {} attempt failed: {}", next_id, exc)
        _run_node_with_retry(by_id[next_id], results, log, exec_ctx)
    return results.get(next_id)


def _build_dag_summary(run_id: str, ordered: list[DAGNode], results: dict,
                       failures: list[str], skipped: list[str]) -> dict[str, Any]:
    """Build final summary dict for the DAG run."""
    rollout_skipped = [
        nid for nid, r in results.items()
        if not r.get("ok") and "[unimplemented]" in (r.get("stderr_tail") or "")
    ] + skipped
    return {
        "run_id": run_id,
        "total": len(ordered),
        "succeeded": len(ordered) - len(failures) - len(skipped),
        "failed": len(failures),
        "skipped": len(skipped),
        "rollout_skipped": rollout_skipped,
        "results": results,
    }


def run_decision_direct(decision_dict: dict[str, Any], run_id: str, max_workers: int = 4,
                        on_progress: Any = None) -> dict[str, Any]:
    if on_progress is not None and not callable(on_progress):
        on_progress = None
    configure_logging()
    init_tracing()
    log = bind_run(run_id)
    exec_ctx = ExecutionContext(run_id=run_id)
    log.info("execution context created: run_id={}", run_id)
    decision = RoutingDecision.model_validate(decision_dict)
    ordered: list[DAGNode] = decision.topological()
    log.info("direct flow start: run_id={} nodes={}", run_id, len(ordered))

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
                if circuit_broken:
                    _drain_inflight(pending, futures, results, on_progress)
                    break
                ready = _find_ready_nodes(pending, futures, by_id, results)
                for nid in ready:
                    futures[nid] = pool.submit(_run_node, by_id[nid], exec_ctx)
                done_now = [nid for nid, f in futures.items() if f.done() and nid in pending]
                if not done_now:
                    next_id = next(nid for nid in futures if nid in pending)
                    r = _block_on_oldest(futures, pending, by_id, results, exec_ctx, log)
                    if _classify_result(next_id, r, failures, skipped, MAX_FAILURES=3):
                        circuit_broken = True
                    pending.discard(next_id)
                    _notify(on_progress, r)
                    continue
                if _process_batch_results(done_now, futures, results, by_id, pending,
                                          failures, skipped, on_progress):
                    circuit_broken = True
    finally:
        if pool is not None:
            pool.shutdown(wait=True)

    completed = len(results)
    log.info("DAG progress: {}/{} nodes done, {} failed, {} skipped",
             completed, len(ordered), len(failures), len(skipped))
    summary = _build_dag_summary(run_id, ordered, results, failures, skipped)
    log.info("direct flow done: {}/{} ok, {} failed, {} skipped",
             summary["succeeded"], summary["total"], summary["failed"], summary["skipped"])
    return summary
