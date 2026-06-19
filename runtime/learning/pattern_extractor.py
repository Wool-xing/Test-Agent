"""Pattern extraction from session history.

Analyzes sessions to detect reusable patterns:
  - Repeated agent sequences (same agents called in same order)
  - Common routing decisions (similar targets -> similar DAGs)
  - Frequent failure modes (which tests fail together)
  - Skill candidates (repeated workflows that could become skills)
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from runtime.learning.session_store import SessionRecord


class PatternExtractor:
    """Analyzes sessions to detect reusable patterns.

    Usage:
        extractor = PatternExtractor()
        patterns = extractor.extract(sessions)
        for p in patterns:
            print(f"{p['type']}: {p['description']} (confidence={p['confidence']})")
    """

    def extract(self, sessions: list[SessionRecord]) -> list[dict]:
        """Analyze sessions and return detected patterns with confidence scores.

        Returns list of dicts with keys:
            type        — "agent_sequence" | "routing" | "failure_mode" | "skill_candidate"
            description — human-readable summary
            confidence  — float 0.0–1.0
            evidence    — list of supporting session ids
            detail      — type-specific payload
        """
        if not sessions:
            return []

        patterns: list[dict] = []
        patterns.extend(self._detect_agent_sequences(sessions))
        patterns.extend(self._detect_common_routing(sessions))
        patterns.extend(self._detect_failure_modes(sessions))
        patterns.extend(self._detect_skill_candidates(sessions))

        # Sort by confidence descending
        patterns.sort(key=lambda p: p["confidence"], reverse=True)
        return patterns

    # ── agent sequence detection ──────────────────────────────────

    def _detect_agent_sequences(self, sessions: list[SessionRecord]) -> list[dict]:
        """Detect repeated sequences of agent calls."""
        # Collect agent chains from sessions
        chains: list[tuple[str, ...]] = []
        for s in sessions:
            agents = []
            for ad in s.agent_decisions:
                name = ad.get("agent", ad.get("name", ""))
                if name:
                    agents.append(name)
            if len(agents) >= 2:
                chains.append(tuple(agents))

        if len(chains) < 2:
            return []

        # Count occurrences of each chain (minimum length 2)
        chain_counts = Counter(chains)
        min_count = max(2, len(sessions) * 0.1)  # at least 10% of sessions

        results = []
        for chain, count in chain_counts.items():
            if count < min_count:
                continue
            confidence = min(count / len(sessions), 1.0)
            if confidence < 0.3:
                continue
            results.append({
                "type": "agent_sequence",
                "description": f"Agent chain '{' -> '.join(chain)}' appears in {count}/{len(sessions)} sessions",
                "confidence": round(confidence, 2),
                "evidence": [s.id for s in sessions if tuple(
                    ad.get("agent", ad.get("name", "")) for ad in s.agent_decisions
                ) == chain],
                "detail": {"agents": list(chain), "occurrences": count},
            })
        return results

    # ── common routing detection ──────────────────────────────────

    def _detect_common_routing(self, sessions: list[SessionRecord]) -> list[dict]:
        """Detect common routing decisions (similar targets -> similar DAGs)."""
        if len(sessions) < 2:
            return []

        # Group by routing_decision shape (node count + first node kind)
        routing_groups: dict[tuple[int, str], list[SessionRecord]] = {}
        for s in sessions:
            rd = s.routing_decision
            nodes = rd.get("nodes", rd.get("dag", []))
            n_count = len(nodes)
            first_kind = nodes[0].get("kind", "") if nodes else ""
            key = (n_count, first_kind)
            routing_groups.setdefault(key, []).append(s)

        results = []
        for (n_count, first_kind), group in routing_groups.items():
            if len(group) < 2:
                continue
            confidence = len(group) / len(sessions)
            if confidence < 0.2:
                continue
            results.append({
                "type": "routing",
                "description": (
                    f"{len(group)} sessions share DAG shape: "
                    f"{n_count} nodes, first={first_kind}"
                ),
                "confidence": round(confidence, 2),
                "evidence": [s.id for s in group],
                "detail": {
                    "node_count": n_count,
                    "first_kind": first_kind,
                    "sample_targets": [s.target for s in group[:3]],
                },
            })
        return results

    # ── failure mode detection ────────────────────────────────────

    def _detect_failure_modes(self, sessions: list[SessionRecord]) -> list[dict]:
        """Detect frequent failure modes (tests that fail together)."""
        # Collect sessions with failures
        failing_sessions = [s for s in sessions if s.outcomes.get("failed", 0) > 0]
        if len(failing_sessions) < 2:
            return []

        # Extract failure reasons from dag_results
        failure_reasons: list[tuple[str, str]] = []
        for s in failing_sessions:
            for dr in s.dag_results:
                error = dr.get("error", "")
                if error:
                    # Truncate and normalize
                    short = error[:80].strip()
                    failure_reasons.append((s.id, short))

        if not failure_reasons:
            return []

        # Look for repeated error messages
        reason_counts = Counter(r for _, r in failure_reasons)
        min_count = max(2, len(failing_sessions) * 0.15)

        results = []
        for reason, count in reason_counts.items():
            if count < min_count:
                continue
            evidence_ids = [sid for sid, r in failure_reasons if r == reason][:10]
            confidence = count / len(failing_sessions)
            results.append({
                "type": "failure_mode",
                "description": f"'{reason[:60]}...' occurs in {count} sessions",
                "confidence": round(confidence, 2),
                "evidence": evidence_ids,
                "detail": {"error_pattern": reason, "occurrences": count},
            })
        return results

    # ── skill candidate detection ─────────────────────────────────

    def _detect_skill_candidates(self, sessions: list[SessionRecord]) -> list[dict]:
        """Detect repeated workflows that could become skills."""
        candidates: list[dict] = []

        # 1. Agent sequence candidates (already detected) — re-evaluate as skills
        agent_sequences = self._detect_agent_sequences(sessions)
        for aseq in agent_sequences:
            if aseq["confidence"] >= 0.5:
                candidates.append({
                    "type": "skill_candidate",
                    "description": (
                        f"Skill candidate: automated workflow for "
                        f"'{' -> '.join(aseq['detail']['agents'])}'"
                    ),
                    "confidence": aseq["confidence"],
                    "evidence": aseq["evidence"],
                    "detail": {
                        "source": "agent_sequence",
                        "agents": aseq["detail"]["agents"],
                        "proposed_skill_name": _make_skill_name(aseq["detail"]["agents"]),
                        "steps": _make_skill_steps(aseq["detail"]["agents"]),
                    },
                })

        # 2. Target-based skill candidates (similar targets tested frequently)
        target_counter = Counter(s.target for s in sessions)
        for target, count in target_counter.items():
            if count < 3:
                continue
            # Only if the target is specific enough (not too short/generic)
            if len(target) < 10:
                continue
            confidence = count / len(sessions)
            if confidence < 0.3:
                continue
            evidence_ids = [s.id for s in sessions if s.target == target]
            candidates.append({
                "type": "skill_candidate",
                "description": (
                    f"Skill candidate: '{target[:60]}' tested {count} times"
                ),
                "confidence": round(confidence, 2),
                "evidence": evidence_ids,
                "detail": {
                    "source": "target_frequency",
                    "target": target,
                    "proposed_skill_name": _slugify(target[:40]),
                    "steps": [
                        "1. Analyze the request and route to appropriate agents",
                        "2. Execute the test workflow",
                        "3. Report results",
                    ],
                },
            })

        return candidates


def _make_skill_name(agents: list[str]) -> str:
    if not agents:
        return "custom-workflow"
    prefix = agents[0].replace("-", "").replace(" ", "")
    return f"auto-{prefix}-workflow"


def _make_skill_steps(agents: list[str]) -> list[str]:
    steps = []
    for i, agent in enumerate(agents, 1):
        steps.append(f"{i}. Call `{agent}` agent")
    steps.append(f"{len(agents) + 1}. Collect and verify results")
    return steps


def _slugify(text: str) -> str:
    """Simple slug for skill names."""
    import re
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:60]
