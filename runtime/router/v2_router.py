"""IntentRouterV2 — Unified router for AI Mode and CLI Mode.

Powered by ManifestV2 catalog + optional KG lookup.
Produces RoutingDecision (same type as V1) for both modes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from loguru import logger

from runtime.router.llm_client import LLMClient, LLMError
from runtime.router.schema import DAGNode, RoutingDecision, TargetArtifact
from runtime.router.v2_prompt import (
    SYSTEM_PROMPT_V2,
    SYSTEM_PROMPT_V2_AI,
    build_catalog_summary,
    build_user_prompt,
)

# ── Keyword routing tables (degraded mode, no LLM) ────────────────────────────

# (keyword_tuple, target_type, expert_nodes, skill_nodes)
_KEYWORD_TABLE: list[tuple[tuple[str, ...], str, list[str], list[str]]] = [
    (
        ("can-bus", "can bus", "ecu", "adas", "v2x", "ota", "asil", "iso 26262", "iso-26262",
         "automotive", "vehicle", "车载", "汽车"),
        "automotive",
        ["requirements-analyst", "testcase-designer", "automotive-tester", "test-executor",
         "bug-manager", "report-generator", "test-lead"],
        [],
    ),
    (
        ("pentest", "penetration test", "sql injection", "xss", "ssrf", "owasp",
         "security testing", "渗透", "渗透测试"),
        "pentest",
        ["requirements-analyst", "testcase-designer", "pentest-tester", "test-executor",
         "bug-manager", "report-generator", "test-lead"],
        ["pentest-coordinator"],
    ),
    (
        ("canvas", "webgl", "ocr", "visual regression", "screenshot diff", "视觉回归", "图像对比"),
        "visual-system",
        ["requirements-analyst", "testcase-designer", "visual-tester", "test-executor",
         "bug-manager", "report-generator", "test-lead"],
        [],
    ),
    (
        ("mqtt", "kafka", "rabbitmq", "jaeger", "iot", "embedded", "modbus", "串口", "serial port"),
        "system-integration",
        ["requirements-analyst", "testcase-designer", "env-manager", "system-tester",
         "test-executor", "bug-manager", "report-generator", "test-lead"],
        [],
    ),
    (
        ("apk", "ipa", "android", "ios", "mobile-app", "mobile", "小程序", "miniprogram"),
        "mobile-app",
        ["requirements-analyst", "testcase-designer", "mobile-tester", "test-executor",
         "bug-manager", "report-generator", "test-lead"],
        [],
    ),
    (
        (".exe", "desktop", "windows", ".msi", ".dmg", "electron", ".app"),
        "desktop-app",
        ["requirements-analyst", "testcase-designer", "desktop-tester", "test-executor",
         "bug-manager", "report-generator", "test-lead"],
        [],
    ),
    (
        ("llm", "ai model", "ai-model", "ml model", "model evaluation", "embedding",
         "推理", "模型", "gpt", "claude"),
        "ai-model",
        ["requirements-analyst", "testcase-designer", "ai-tester", "test-executor",
         "bug-manager", "report-generator", "test-lead"],
        [],
    ),
    (
        ("rest api", "rest-api", "grpc", "graphql", "api", "endpoint", "openapi", "swagger",
         "接口"),
        "rest-api",
        ["requirements-analyst", "testcase-designer", "automation-engineer", "test-executor",
         "bug-manager", "report-generator", "test-lead"],
        [],
    ),
]

_DEFAULT_KEYWORD = (
    "web-system",
    ["requirements-analyst", "testcase-designer", "env-manager", "data-preparer",
     "automation-engineer", "test-executor", "bug-manager", "report-generator", "test-lead"],
    [],
)


class IntentRouterV2:
    """Unified router for AI Mode and CLI Mode.

    AI Mode: called as a tool by Claude Code
    CLI Mode: called directly by tagent run/plan
    """

    def __init__(self, specs_root: Path | None = None) -> None:
        self._specs_root = specs_root or (Path(__file__).resolve().parents[2] / "specs")
        self._catalog = self._load_catalog()
        self._name_index: dict[str, dict] = self._build_name_index()

    # ── Catalog loading ─────────────────────────────────────────────────────

    def _load_catalog(self) -> dict[str, Any]:
        """Load catalog from ManifestV2 files in specs/."""
        return build_catalog_summary(self._specs_root)

    def _build_name_index(self) -> dict[str, dict]:
        """Build a lookup index by name for fast validation."""
        index: dict[str, dict] = {}
        for entry in self._catalog.get("agents", []):
            index[entry["name"]] = entry
        for entry in self._catalog.get("skills", []):
            index[entry["name"]] = entry
        return index

    @property
    def agent_count(self) -> int:
        return len(self._catalog.get("agents", []))

    @property
    def skill_count(self) -> int:
        return len(self._catalog.get("skills", []))

    # ── Routing ─────────────────────────────────────────────────────────────

    def route(
        self,
        target: str,
        mode: str = "cli",
        *,
        client: LLMClient | None = None,
    ) -> RoutingDecision:
        """Route user intent to DAG of agents/skills.

        Args:
            target: User input (PRD path, URL, free text)
            mode: 'cli', 'ai', or 'plan'
            client: Optional LLM client (auto-creates if None)

        Returns:
            RoutingDecision with DAG of agents/skills
        """
        # 1. Try LLM-based routing
        try:
            return self._route_via_llm(target, mode, client)
        except (LLMError, RouterV2Error):
            logger.info("LLM routing failed, falling back to keyword routing")
        except Exception as e:
            logger.warning("LLM routing unexpected error: {}", e)

        # 2. Fallback: keyword-based routing (no LLM needed)
        return self._route_via_keywords(target, mode)

    def plan_only(self, target: str) -> RoutingDecision:
        """Route without execution -- returns DAG for user review."""
        return self.route(target, mode="plan")

    # ── LLM routing ─────────────────────────────────────────────────────────

    def _route_via_llm(
        self, target: str, mode: str, client: LLMClient | None
    ) -> RoutingDecision:
        # Stub provider: skip LLM, fall through to keyword routing
        if client is not None and client.provider == "stub":
            raise RouterV2Error("stub provider: delegating to keyword routing")

        client = client or LLMClient()

        system = SYSTEM_PROMPT_V2_AI if mode == "ai" else SYSTEM_PROMPT_V2
        user = build_user_prompt(target, self._catalog)

        try:
            raw = client.complete_json(system, user)
        except LLMError:
            raise RouterV2Error("LLM unavailable for V2 routing")

        try:
            decision = RoutingDecision.model_validate(raw)
        except Exception as e:
            raise RouterV2Error(f"LLM output invalid: {e}")

        # Validate against manifest catalog
        issues = self._validate_decision(decision)
        if issues:
            logger.warning("V2 decision validation issues: {}", issues)
            if decision.confidence > 0.5:
                decision.confidence = max(0.0, decision.confidence - 0.3)

        return decision

    # ── Keyword-based routing (degraded mode) ───────────────────────────────

    def _route_via_keywords(self, target: str, mode: str) -> RoutingDecision:
        """Keyword-based routing fallback. No LLM required."""
        target_lower = target.lower()

        # Check if target is a PRD file path
        if target.endswith((".md", ".pdf", ".docx", ".xlsx", ".txt")):
            try:
                path = Path(target)
                if path.is_file():
                    target_lower += " " + path.read_text(encoding="utf-8", errors="ignore")[:2000].lower()
            except Exception:
                pass

        # Match against keyword tables
        detected_type, expert_names, skill_names = _DEFAULT_KEYWORD
        for keywords, t, exp, skl in _KEYWORD_TABLE:
            if any(k in target_lower for k in keywords):
                detected_type, expert_names, skill_names = t, exp, skl
                break

        # Build DAG from matched names
        nodes: list[DAGNode] = []
        prev_id: str | None = None
        nid = 0

        # Skills first (e.g. pentest-coordinator)
        for name in skill_names:
            nodes.append(DAGNode(
                id=f"n{nid}", kind="skill", name=name,
                depends_on=[],
                one_liner_zh=f"执行{name}技能",
            ))
            prev_id = f"n{nid}"
            nid += 1

        # Then experts
        for name in expert_names:
            depends = [prev_id] if prev_id else []
            nodes.append(DAGNode(
                id=f"n{nid}", kind="expert", name=name,
                depends_on=depends,
                one_liner_zh=f"调用{name}专家",
            ))
            prev_id = f"n{nid}"
            nid += 1

        # Validate against catalog
        decision = RoutingDecision(
            dag=nodes,
            rationale=f"Keyword-based routing: matched target type '{detected_type}'",
            confidence=0.5,
            detected_target_type=detected_type,
            detected_qualities=["functional", "regression"],
            missing_inputs=[],
        )
        issues = self._validate_decision(decision)
        if issues:
            logger.warning("keyword decision validation issues: {}", issues)

        return decision

    # ── Validation ──────────────────────────────────────────────────────────

    def _validate_decision(self, decision: RoutingDecision) -> list[str]:
        """Validate routing decision against the manifest catalog.

        Note: DAGNode.kind uses 'expert' (legacy naming from V1 schema).
        ManifestV2 uses 'agent'. We treat them as equivalent.
        """
        issues: list[str] = []

        # Map DAG kind to catalog kind for validation
        _KIND_MAP = {"expert": "agent", "skill": "skill"}

        for node in decision.dag:
            if node.kind not in ("expert", "skill"):
                continue

            entry = self._name_index.get(node.name)
            if entry is None:
                issues.append(
                    f"unknown {node.kind} '{node.name}' (id={node.id}): "
                    f"not found in ManifestV2 catalog"
                )
                continue

            expected_catalog_kind = _KIND_MAP.get(node.kind)
            if expected_catalog_kind and entry.get("kind") != expected_catalog_kind:
                issues.append(
                    f"kind mismatch for '{node.name}' (id={node.id}): "
                    f"DAG says '{node.kind}', catalog says '{entry.get('kind')}'"
                )

        # Check DAG topology
        try:
            decision.topological()
        except ValueError as e:
            issues.append(str(e))

        return issues


class RouterV2Error(RuntimeError):
    """Error from IntentRouterV2."""
    pass
