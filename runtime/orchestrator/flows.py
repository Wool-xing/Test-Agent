"""Prefect flow: run a RoutingDecision end-to-end."""

from __future__ import annotations

from typing import Any

from loguru import logger
from prefect import flow
from prefect.task_runners import ConcurrentTaskRunner

from runtime.observability.logging import bind_run, configure_logging
from runtime.observability.otel import init_tracing, span
from runtime.orchestrator.adapters.experts import reset_upstream_cache
from runtime.orchestrator.tasks import execute_dag_node
from runtime.router.schema import DAGNode, RoutingDecision


@flow(name="test-agent-run", task_runner=ConcurrentTaskRunner())
def run_decision_flow(decision_dict: dict[str, Any], run_id: str) -> dict[str, Any]:
    configure_logging()
    init_tracing()
    log = bind_run(run_id)
    reset_upstream_cache()  # V1.14 主宪章 §40 — 每 run 清 runner 间产物缓存
    decision = RoutingDecision.model_validate(decision_dict)
    ordered: list[DAGNode] = decision.topological()
    log.info("flow start: run_id={} nodes={}", run_id, len(ordered))

    results: dict[str, dict] = {}
    failures: list[str] = []
    with span("flow.run", run_id=run_id, nodes=len(ordered)):
        # Submit in topological order; nodes with all deps done fire immediately.
        futures: dict[str, Any] = {}
        for node in ordered:
            wait_for = [futures[d] for d in node.depends_on if d in futures]
            futures[node.id] = execute_dag_node.submit(node, wait_for=wait_for)
        for nid, fut in futures.items():
            try:
                results[nid] = fut.result()
                if not results[nid].get("ok"):
                    failures.append(nid)
            except Exception as e:  # noqa: BLE001
                log.error("node {} crashed: {}", nid, e)
                results[nid] = {"id": nid, "ok": False, "error": str(e)}
                failures.append(nid)

    summary = {
        "run_id": run_id,
        "total": len(ordered),
        "succeeded": len(ordered) - len(failures),
        "failed": len(failures),
        "results": results,
    }
    log.info("flow done: {}/{} ok", summary["succeeded"], summary["total"])
    return summary
