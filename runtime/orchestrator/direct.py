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
from runtime.orchestrator.adapters.experts import execute_node
from runtime.router.schema import DAGNode, RoutingDecision


def _run_node(node: DAGNode) -> dict[str, Any]:
    with span(f"node.{node.kind}.{node.name}", node_id=node.id):
        outcome = execute_node(name=node.name, kind=node.kind, inputs=node.inputs, timeout=node.timeout_seconds)
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
    if not outcome.ok and node.on_failure == "abort":
        raise RuntimeError(f"node {node.id} aborted: rc={outcome.returncode}")
    return summary


def run_decision_direct(decision_dict: dict[str, Any], run_id: str, max_workers: int = 4) -> dict[str, Any]:
    configure_logging()
    init_tracing()
    log = bind_run(run_id)
    decision = RoutingDecision.model_validate(decision_dict)
    ordered: list[DAGNode] = decision.topological()
    log.info("direct flow start: run_id={} nodes={}", run_id, len(ordered))

    by_id: dict[str, DAGNode] = {n.id: n for n in ordered}
    results: dict[str, dict] = {}
    failures: list[str] = []
    pending = set(by_id.keys())
    futures: dict[str, Future] = {}
    pool = ThreadPoolExecutor(max_workers=max_workers)
    try:
        with span("flow.run", run_id=run_id, nodes=len(ordered)):
            while pending:
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
                        if not results[next_id].get("ok"):
                            failures.append(next_id)
                    except Exception as e:  # noqa: BLE001
                        log.error("node {} crashed: {}", next_id, e)
                        results[next_id] = {"id": next_id, "ok": False, "error": str(e)}
                        failures.append(next_id)
                    pending.discard(next_id)
                    continue
                for nid in done_now:
                    try:
                        results[nid] = futures[nid].result()
                        if not results[nid].get("ok"):
                            failures.append(nid)
                    except Exception as e:  # noqa: BLE001
                        log.error("node {} crashed: {}", nid, e)
                        results[nid] = {"id": nid, "ok": False, "error": str(e)}
                        failures.append(nid)
                    pending.discard(nid)
    finally:
        pool.shutdown(wait=True)

    summary = {
        "run_id": run_id,
        "total": len(ordered),
        "succeeded": len(ordered) - len(failures),
        "failed": len(failures),
        "results": results,
    }
    log.info("direct flow done: {}/{} ok", summary["succeeded"], summary["total"])
    return summary
