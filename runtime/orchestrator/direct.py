"""Prefect-less direct executor.

Used when Prefect isn't installed (early demos, CI smoke). Same input/output
contract as `flows.run_decision_flow` so callers can transparently fall back.
"""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

from loguru import logger

from runtime.observability.logging import bind_run, configure_logging
from runtime.observability.otel import init_tracing, span
from runtime.orchestrator.adapters.experts import execute_node, reset_upstream_cache
from runtime.router.schema import DAGNode, RoutingDecision
from runtime.self_healing.retry import with_retry


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


def run_decision_direct(decision_dict: dict[str, Any], run_id: str, max_workers: int = 4) -> dict[str, Any]:
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
                    break
                # find nodes whose deps are all done
                ready = [
                    nid
                    for nid in list(pending)
                    if all(d in results for d in by_id[nid].depends_on) and nid not in futures
                ]
                for nid in ready:
                    futures[nid] = pool.submit(_run_node, by_id[nid])
                # wait for at least one to finish
                done_now = [nid for nid, f in futures.items() if f.done() and nid in pending]
                if not done_now:
                    # block on the oldest pending future
                    next_id = next(iter(futures))
                    try:
                        results[next_id] = futures[next_id].result()
                    except Exception as e:  # noqa: BLE001
                        log.warning("node {} attempt failed: {}", next_id, e)
                        for attempt in range(2):
                            time.sleep(2**attempt)
                            try:
                                fut = pool.submit(_run_node, by_id[next_id])
                                results[next_id] = fut.result()
                                break
                            except Exception as retry_exc:  # noqa: BLE001
                                log.warning("node {} retry {}/2 failed", next_id, attempt + 1)
                                if attempt == 1:
                                    results[next_id] = {"id": next_id, "ok": False, "error": str(retry_exc)}
                    if results.get(next_id):
                        if results[next_id].get("skipped"):
                            skipped.append(next_id)
                        elif not results[next_id].get("ok"):
                            failures.append(next_id)
                            if len(failures) >= MAX_FAILURES:
                                log.error("circuit breaker: {} failures, aborting DAG", len(failures))
                                circuit_broken = True
                    pending.discard(next_id)
                    continue
                for nid in done_now:
                    try:
                        results[nid] = futures[nid].result()
                    except Exception as e:  # noqa: BLE001
                        log.warning("node {} attempt failed: {}", nid, e)
                        for attempt in range(2):
                            time.sleep(2**attempt)
                            try:
                                fut = pool.submit(_run_node, by_id[nid])
                                results[nid] = fut.result()
                                break
                            except Exception as retry_exc:  # noqa: BLE001
                                log.warning("node {} retry {}/2 failed", nid, attempt + 1)
                                if attempt == 1:
                                    results[nid] = {"id": nid, "ok": False, "error": str(retry_exc)}
                    if results.get(nid):
                        if results[nid].get("skipped"):
                            skipped.append(nid)
                        elif not results[nid].get("ok"):
                            failures.append(nid)
                            if len(failures) >= MAX_FAILURES:
                                log.error("circuit breaker: {} failures, aborting DAG", len(failures))
                                circuit_broken = True
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
