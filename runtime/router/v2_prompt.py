"""Prompt builder for IntentRouterV2.

Builds a compact catalog summary from ManifestV2 files,
adds KG context if available, and includes structured output
instructions for RoutingDecision JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from specs.manifest import Kind

# ── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT_V2 = """You are the Test-Agent Intent Router v2.

Your job: given a user's testing intent (PRD path, URL, free text description),
choose which AGENTS and SKILLS from the catalog must run, in what order, to
produce a complete test plan and result.

HARD RULES:
1. Output ONE JSON object only. No prose, no markdown fences.
2. Schema (per node, all fields lowercase, exact spelling):
   {
     "dag": [
        {"id": "n0", "kind": "expert|skill|script", "name": "<catalog name>",
         "depends_on": ["..."], "dep_mode": "hard|soft", "inputs": {},
         "on_failure": "retry|skip|abort", "timeout_seconds": 1800,
         "one_liner_zh": "<=30 chars why (required)",
         "one_liner_en": "Short rationale in English (<=120 chars)"}
     ],
     "rationale": "<=3 sentences, why this combination",
     "confidence": 0.0-1.0,
     "detected_target_type": "web-system|rest-api|mobile-app|desktop-app|docker-image|ai-model|middleware|embedded|other",
     "detected_qualities": ["functional", "performance", "security", ...],
     "missing_inputs": ["any required info the user did not provide"]
   }
3. Names MUST come from the provided catalog. Do not invent agents or skills.
4. Topological consistency: depends_on must reference earlier ids that exist.
5. Pick the MINIMUM set that covers the detected qualities.
6. Always start with 'requirements-analyst' unless input is already structured JSON.
7. Always end with 'bug-manager' -> 'report-generator' -> 'test-lead' if any execution agent is present.
8. For mobile/desktop/visual/system/ai targets, route the corresponding platform agent.
9. If confidence < 0.6, list missing_inputs so the caller can prompt user.
10. one_liner_zh is REQUIRED for every node.
"""

SYSTEM_PROMPT_V2_AI = SYSTEM_PROMPT_V2 + """
AI MODE instructions:
- You are being called as a tool by a Claude Code agent.
- The agent will use your RoutingDecision to spawn sub-agents and invoke skills.
- Prefer skill nodes over expert nodes when a skill covers the same ground with less overhead.
- Include theory_refs and alternatives when available for learn-mode transparency.
"""


# ── Catalog builder from ManifestV2 ─────────────────────────────────────────


def _load_manifest(path: Path) -> dict[str, Any] | None:
    """Load and validate a single ManifestV2 YAML file.

    Falls back to raw YAML extraction when ManifestV2 validation fails
    (e.g. backend=script with no script_path), so the catalog remains
    complete even when manifests have minor schema issues.
    """
    import yaml

    from specs.manifest import ManifestV2

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None

    try:
        m = ManifestV2.model_validate(raw)
    except Exception:
        # Graceful fallback: extract fields from raw YAML
        m = None

    # Determine fields from validated model or raw dict
    if m is not None:
        name = m.name
        kind = m.kind.value
        description = m.description
        description_zh = m.description_zh
        backend = m.backend.value
        tags = m.tags
        tools = m.tools
        deprecated = m.deprecated
    else:
        name = raw.get("name", "")
        kind = raw.get("kind", "")
        if not name or not kind:
            return None
        description = raw.get("description", "")
        description_zh = raw.get("description_zh", "")
        backend = raw.get("backend", "llm")
        tags = raw.get("tags", []) or []
        tools = raw.get("tools", []) or []
        deprecated = raw.get("deprecated", False)

    if deprecated:
        return None
    return {
        "name": name,
        "kind": kind,
        "description": description,
        "description_zh": description_zh,
        "backend": backend,
        "tags": tags,
        "tools": tools,
    }


def build_catalog_summary(specs_root: Path | None = None) -> dict[str, Any]:
    """Build a compact catalog summary from ManifestV2 files.

    Returns a dict with 'agents' and 'skills' lists suitable for the LLM prompt.
    """
    if specs_root is None:
        specs_root = Path(__file__).resolve().parents[2] / "specs"

    agents: list[dict[str, Any]] = []
    skills: list[dict[str, Any]] = []

    agents_dir = specs_root / "agents"
    if agents_dir.is_dir():
        for manifest_path in sorted(agents_dir.glob("*/manifest.yaml")):
            entry = _load_manifest(manifest_path)
            if entry:
                agents.append(entry)

    skills_dir = specs_root / "skills"
    if skills_dir.is_dir():
        for manifest_path in sorted(skills_dir.glob("*/manifest.yaml")):
            entry = _load_manifest(manifest_path)
            if entry:
                skills.append(entry)

    return {"agents": agents, "skills": skills}


# ── KG context ───────────────────────────────────────────────────────────────


def _load_kg_context(graph_path: Path, target_text: str, top_k: int = 5) -> dict[str, Any] | None:
    """Query the knowledge graph for relevant historical patterns.

    Uses a lightweight keyword-based search over node labels in graph.json.
    """
    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    nodes = graph.get("nodes", [])
    if not nodes or not target_text:
        return None

    query_lower = target_text.lower()
    scored: list[tuple[float, dict]] = []

    for node in nodes:
        label = (node.get("label") or "").lower()
        norm = (node.get("norm_label") or "").lower()
        community = node.get("community", -1)
        source_file = node.get("source_file", "")

        # Simple relevance: count keyword overlap
        score = 0.0
        for word in query_lower.split():
            if word and len(word) > 2:
                if word in label:
                    score += 0.5
                if word in norm:
                    score += 0.3
                if word in source_file:
                    score += 0.2

        if score > 0:
            scored.append((score, node))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]

    if not top:
        return None

    communities = list({n[1].get("community") for n in top if n[1].get("community", -1) >= 0})
    labels = [n[1].get("label", "") for n in top]

    return {
        "top_nodes": labels,
        "top_communities": communities,
        "total_nodes_searched": len(nodes),
        "hint": "These are relevant codebase areas. Consider if the test target relates to any of them.",
    }


def build_kg_block(target_text: str) -> str:
    """Build a KG context block for the prompt, or empty string if unavailable."""
    graph_path = Path(__file__).resolve().parents[2] / "graphify-out" / "graph.json"
    if not graph_path.is_file():
        return ""

    ctx = _load_kg_context(graph_path, target_text)
    if ctx is None:
        return ""

    lines = [
        "# Knowledge Graph Context",
        f"Top relevant codebase areas: {ctx['top_nodes']}",
        f"Related communities: {ctx['top_communities']}",
        f"(Searched {ctx['total_nodes_searched']} nodes in the project knowledge graph)",
        "Use this to ground routing decisions in the actual codebase structure.",
        "",
    ]
    return "\n".join(lines)


# ── User prompt builder ─────────────────────────────────────────────────────


def build_user_prompt(
    target: str,
    catalog: dict | None = None,
    *,
    include_kg: bool = True,
) -> str:
    """Build the complete user prompt for the V2 router.

    Args:
        target: User input (PRD path, URL, or free text)
        catalog: Pre-built catalog summary (loads fresh if None)
        include_kg: Whether to include KG context
    """
    if catalog is None:
        catalog = build_catalog_summary()

    parts: list[str] = []

    parts.append("CATALOG (from ManifestV2 specs/):")
    parts.append(json.dumps(catalog, ensure_ascii=False, indent=2))

    if include_kg:
        kg_block = build_kg_block(target)
        if kg_block:
            parts.append(kg_block)

    parts.append("TARGET:")
    parts.append(target)
    parts.append("")
    parts.append("Return the routing JSON now. Be precise about catalog names.")

    return "\n".join(parts)
