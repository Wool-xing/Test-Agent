"""Shared service kernel used by both api and cli."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from runtime.config.settings import get_settings
from runtime.observability.logging import configure_logging
from runtime.registry.registry import get_catalog
from runtime.router.llm_client import LLMClient
from runtime.router.router import route
from runtime.router.schema import RoutingDecision, TargetArtifact
from runtime.storage.models import RunStatus
from runtime.storage.repo import create_run, set_run_status


class Kernel:
    """Coarse-grained operations used by api/cli."""

    def __init__(self) -> None:
        configure_logging()
        self.settings = get_settings()

    # ---------- routing ----------
    def decide(self, artifact: TargetArtifact, *, vote_providers: list[str] | None = None) -> RoutingDecision:
        if vote_providers:
            from runtime.router.router import route_with_vote

            return route_with_vote(artifact, vote_providers)
        client = LLMClient()
        return route(artifact, client=client)

    # ---------- run lifecycle ----------
    def submit(self, artifact: TargetArtifact, *, persist: bool = True) -> tuple[str, RoutingDecision]:
        decision = self.decide(artifact)
        # V1.14 主宪章 §40 — 把原始 artifact 文本注入每节点 inputs,让 AgentRunner 拿得到
        full_text = artifact.text or ""
        if not full_text and artifact.path:
            try:
                full_text = Path(artifact.path).read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                logger.warning("cannot read artifact {}: {}", artifact.path, e)
                full_text = f"[READ_ERROR: {artifact.path}]"
        for node in decision.dag:
            if "artifact_text" not in node.inputs:
                node.inputs["artifact_text"] = full_text[:20_000]
        target_summary = (artifact.text or artifact.path or "")[:400]
        if persist:
            try:
                run_id = create_run(target_summary, decision.detected_target_type, decision.model_dump())
            except Exception as e:  # noqa: BLE001
                logger.error("persistence unavailable — run results will not be saved: {}", e)
                run_id = _ephemeral_run_id()
        else:
            run_id = _ephemeral_run_id()
        return run_id, decision

    def execute_sync(self, run_id: str, decision: RoutingDecision, on_progress: Any = None) -> dict[str, Any]:
        try:
            self._safe_set_status(run_id, RunStatus.running)
            summary = _run_decision(decision.model_dump(), run_id, on_progress=on_progress)
            ok = summary["failed"] == 0
            self._safe_set_status(run_id, RunStatus.succeeded if ok else RunStatus.failed)
            return summary
        except Exception as e:  # noqa: BLE001
            logger.exception("flow crashed: {}", e)
            self._safe_set_status(run_id, RunStatus.failed)
            raise

    def _safe_set_status(self, run_id: str, status: RunStatus) -> None:
        try:
            set_run_status(run_id, status)
        except Exception as e:  # noqa: BLE001
            logger.warning("status persist skipped for {} ({}): {}", run_id, status.value, e)

    # ---------- catalog ----------
    def catalog(self) -> dict:
        cat = get_catalog(refresh=True)
        return cat.to_dict() | {"counts": {"experts": len(cat.experts), "skills": len(cat.skills)}}


def _ephemeral_run_id() -> str:
    import uuid

    return "ephem-" + uuid.uuid4().hex[:16]


def _run_decision(decision_dict: dict, run_id: str, on_progress: Any = None) -> dict:
    """Use Prefect flow if available, else direct executor."""
    try:
        from runtime.orchestrator.flows import run_decision_flow

        return run_decision_flow(decision_dict, run_id, on_progress=on_progress)
    except (ImportError, RuntimeError) as e:
        logger.debug("prefect unavailable ({}); using direct executor", e)
        from runtime.orchestrator.direct import run_decision_direct

        return run_decision_direct(decision_dict, run_id, on_progress=on_progress)
