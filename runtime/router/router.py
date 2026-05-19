"""Main router: artifact -> RoutingDecision."""

from __future__ import annotations

from loguru import logger
from pydantic import ValidationError

from runtime.registry.registry import Catalog, get_catalog
from runtime.router.llm_client import LLMClient, LLMError
from runtime.router.prompt import SYSTEM_PROMPT, build_user_prompt
from runtime.router.schema import RoutingDecision, TargetArtifact

try:
    from runtime.router.retrieval import build_similar_examples_block

    _HISTORY_AVAILABLE = True
except ImportError:
    _HISTORY_AVAILABLE = False
    build_similar_examples_block = None  # type: ignore


class RouterError(RuntimeError):
    pass


def _validate_against_catalog(decision: RoutingDecision, catalog: Catalog) -> list[str]:
    issues: list[str] = []

    # V1.14 防 mock (ROADMAP V1.15 Day 0 承诺): 检查 expert / skill 实装状态
    # 单源: catalog entry.impl_status (agents/skills .md frontmatter)
    # rollout / vision / unknown 状态 router 仍可路由,但 issues 列表标 warning + downgrade confidence
    # → orchestrator execute_node 跑到时会硬拒并报明确错误 (returncode=2),不输出 mock 数据
    for n in decision.dag:
        if n.kind not in ("expert", "skill"):
            continue
        entry = catalog.lookup(n.name)
        if entry is None or entry.kind != n.kind:
            issues.append(f"unknown {n.kind} '{n.name}' (id={n.id})")
            continue
        if entry.impl_status in ("rollout", "vision"):
            issues.append(
                f"{n.kind} '{n.name}' 处于 V1.x {entry.impl_status} (id={n.id}); "
                f"test-lead 决策应降级 conditional 或 no-go"
            )
        elif entry.impl_status == "unknown":
            issues.append(
                f"{n.kind} '{n.name}' frontmatter "
                f"{'EXPERT' if n.kind == 'expert' else 'SKILL'}_IMPL_STATUS 缺失或非法 (id={n.id})"
            )
    try:
        decision.topological()
    except ValueError as e:
        issues.append(str(e))
    return issues


def route(
    artifact: TargetArtifact,
    *,
    client: LLMClient | None = None,
    use_history: bool = True,
) -> RoutingDecision:
    """Single-shot route. Caller decides whether to fallback / vote.

    Args:
        use_history: when True and history retrieval is wired, prepend top-k similar
                     past decisions as few-shot examples (flywheel feedback loop §M2-9).
    """
    cat = get_catalog()
    client = client or LLMClient()
    user = build_user_prompt(artifact, cat)
    if use_history and _HISTORY_AVAILABLE and (artifact.text or artifact.path):
        try:
            block = build_similar_examples_block(artifact, top_k=3)
            if block:
                user = block + "\n\n" + user
        except Exception as e:  # noqa: BLE001
            logger.debug("history retrieval skipped: {}", e)
    try:
        raw = client.complete_json(SYSTEM_PROMPT, user)
    except LLMError as e:
        raise RouterError(f"LLM unavailable: {e}") from e
    try:
        decision = RoutingDecision.model_validate(raw)
    except ValidationError as e:
        raise RouterError(f"router output invalid: {e}") from e
    issues = _validate_against_catalog(decision, cat)
    if issues:
        logger.warning("decision validation issues: {}", issues)
        if decision.confidence > 0.5:
            decision.confidence = max(0.0, decision.confidence - 0.3)
    return decision


def route_with_vote(artifact: TargetArtifact, providers: list[str]) -> RoutingDecision:
    """Two+-model vote. If decisions disagree on detected_target_type, lower confidence and merge experts (union)."""
    decisions: list[RoutingDecision] = []
    for prov in providers:
        try:
            decisions.append(route(artifact, client=LLMClient(provider=prov)))
        except RouterError as e:
            logger.warning("vote: provider {} failed: {}", prov, e)
    if not decisions:
        raise RouterError("all vote providers failed")
    if len(decisions) == 1:
        return decisions[0]
    types = {d.detected_target_type for d in decisions}
    if len(types) == 1:
        return max(decisions, key=lambda d: d.confidence)
    # disagreement: union dag node names by name+kind, take highest confidence as base, downgrade
    base = max(decisions, key=lambda d: d.confidence)
    base.confidence = max(0.0, base.confidence - 0.2)
    base.rationale += " (vote disagreement; downgraded confidence)"
    return base
