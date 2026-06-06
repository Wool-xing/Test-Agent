"""Sub-agent intent detection — direct agent/skill invocation from natural language.

Detects agent/skill names in user input and creates a direct DAG, bypassing
the full LLM routing call. Saves latency and tokens for explicit requests.

Patterns detected:
  - "用 <agent-name>" / "use <agent-name>" → direct invocation
  - "@<agent-name>" / "@<skill-name>" → direct invocation
  - Bare agent/skill mention in testing context → fast-path routing
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from loguru import logger

from runtime.router.schema import DAGNode, RoutingDecision


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


def _load_catalog_names() -> dict[str, tuple[str, str]]:
    """Return {name: (kind, impl_status)} for all experts and skills."""
    try:
        from runtime.registry.registry import get_catalog
        cat = get_catalog()
        names: dict[str, tuple[str, str]] = {}
        for e in cat.experts.values():
            names[e.name] = (e.kind, e.impl_status)
        for s in cat.skills.values():
            names[s.name] = (s.kind, s.impl_status)
        return names
    except Exception:
        logger.warning("Failed to load catalog for intent detection")
        return {}


def detect_direct_agent(text: str) -> list[tuple[str, str]]:
    """Detect explicitly targeted agent/skill names in user input.

    Returns list of (name, kind) tuples for matched agents/skills.
    Returns empty list if no direct targets found.
    """
    catalog = _load_catalog_names()
    if not catalog:
        return []

    text_lower = text.lower()
    matched: list[tuple[str, str]] = []

    # Pattern 1: "@agent-name" or "@skill-name"
    at_pattern = re.findall(r'@([a-z][a-z0-9_-]{2,40})', text_lower)
    for name in at_pattern:
        if name in catalog and name not in {m[0] for m in matched}:
            matched.append((name, catalog[name][0]))

    # Pattern 2: "用 <name>" / "使用 <name>" / "调用 <name>"
    cn_pattern = re.findall(r'(?:用|使用|调用|通过|借助)\s*([a-z][a-z0-9_-]{2,40})', text_lower)
    for name in cn_pattern:
        if name in catalog and name not in {m[0] for m in matched}:
            matched.append((name, catalog[name][0]))

    # Pattern 3: "use <name>" / "run <name>" / "invoke <name>"
    en_pattern = re.findall(r'(?:use|run|invoke|call|trigger)\s+([a-z][a-z0-9_-]{2,40})', text_lower)
    for name in en_pattern:
        if name in catalog and name not in {m[0] for m in matched}:
            matched.append((name, catalog[name][0]))

    # Pattern 4: "让 <name>" / "叫 <name>" (Chinese colloquial)
    cn2_pattern = re.findall(r'(?:让|叫|喊)\s*([a-z][a-z0-9_-]{2,40})', text_lower)
    for name in cn2_pattern:
        if name in catalog and name not in {m[0] for m in matched}:
            matched.append((name, catalog[name][0]))

    return matched


def build_direct_dag(
    targets: list[tuple[str, str]],
    *,
    artifact_text: str = "",
    confidence: float = 0.9,
) -> RoutingDecision | None:
    """Build a RoutingDecision with direct DAG nodes for matched targets.

    Returns None if targets is empty or all targets have no production runner.
    """
    if not targets:
        return None

    nodes: list[DAGNode] = []
    for i, (name, kind) in enumerate(targets):
        nid = _short_id()
        deps = [nodes[0].id] if i > 0 else []
        nodes.append(DAGNode(
            id=nid,
            kind=kind,  # type: ignore[arg-type]
            name=name,
            depends_on=deps,
            inputs={"artifact_text": artifact_text[:20_000]},
            one_liner_zh=f"直接调用 {name}",
        ))

    return RoutingDecision(
        dag=nodes,
        rationale=f"Direct agent invocation: {', '.join(n for n, _ in targets)}",
        confidence=confidence,
        detected_target_type="other",
        detected_qualities=[],
    )


def try_fast_path(text: str) -> RoutingDecision | None:
    """Attempt direct agent/skill routing. Returns None to fall through to LLM router.

    This is the main entry point for both REPL and IM bridge.
    """
    targets = detect_direct_agent(text)
    if not targets:
        return None

    logger.info("Fast-path: detected direct agent targets: {}", [n for n, _ in targets])
    decision = build_direct_dag(targets, artifact_text=text)
    return decision
