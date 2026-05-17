"""Prefect tasks (atomic units)."""

from __future__ import annotations

from loguru import logger
from prefect import task
from prefect.tasks import exponential_backoff

from runtime.orchestrator.adapters.experts import StepOutcome, execute_node
from runtime.observability.otel import span
from runtime.router.schema import DAGNode


@task(retries=2, retry_delay_seconds=exponential_backoff(backoff_factor=5), timeout_seconds=3600)
def execute_dag_node(node: DAGNode) -> dict:
    """Atomic node execution. Returns serializable summary."""
    with span(f"node.{node.kind}.{node.name}", node_id=node.id):
        outcome: StepOutcome = execute_node(
            name=node.name,
            kind=node.kind,
            inputs=node.inputs,
            timeout=node.timeout_seconds,
        )
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
    if not outcome.ok:
        if node.on_failure == "abort":
            logger.error("node {} failed (abort): {}", node.id, outcome.stderr[-500:])
            raise RuntimeError(f"node {node.id} failed with rc={outcome.returncode}")
        if node.on_failure == "skip":
            summary["skipped"] = True
            logger.info("node {} skipped per on_failure=skip", node.id)
        else:
            logger.warning("node {} failed (on_failure={}): {}", node.id, node.on_failure, outcome.stderr[-200:])
    return summary
