"""Curator — 7-day cycle agent for cross-session learning.

Reviews skill candidates from pattern extraction, accepts/rejects based on
confidence thresholds, and writes accepted skill manifests to disk.

Extends the existing learning_loop/curator.py coordinator with a higher-level
analysis cycle.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from runtime.learning.pattern_extractor import PatternExtractor
from runtime.learning.session_store import SessionStore

logger = logging.getLogger(__name__)

# ── defaults ──────────────────────────────────────────────────────

_ACCEPT_THRESHOLD = 0.7
_CYCLE_DAYS = 7
_MAX_ACCEPTED_PER_CYCLE = 5


class Curator:
    """7-day cycle curator agent.

    Reviews skill candidates extracted from session patterns, accepts or rejects
    them based on confidence, and writes accepted skill manifests to
    specs/skills/learned/.

    Usage:
        store = SessionStore(Path("workspace/_test_sessions.db"))
        curator = Curator(store)
        result = curator.run_cycle()
        # result: {"accepted": 2, "rejected": 3, "pending": 1,
        #          "cycle_ts": "2026-06-19T...", "notes": [...]}
    """

    def __init__(
        self,
        session_store: SessionStore,
        *,
        accept_threshold: float = _ACCEPT_THRESHOLD,
        cycle_days: int = _CYCLE_DAYS,
        max_accepted: int = _MAX_ACCEPTED_PER_CYCLE,
        learned_skills_dir: Path | None = None,
    ):
        self.store = session_store
        self.accept_threshold = accept_threshold
        self.cycle_days = cycle_days
        self.max_accepted = max_accepted
        self.learned_skills_dir = learned_skills_dir or Path("specs/skills/learned")
        self._extractor = PatternExtractor()

    def run_cycle(self) -> dict[str, Any]:
        """Run one curation cycle.

        Returns dict with accepted/rejected/pending counts, cycle timestamp,
        and detailed notes.
        """
        cycle_ts = datetime.now(timezone.utc).isoformat()
        notes: list[str] = []

        # 1. Load sessions from the cycle window
        cutoff = (datetime.now(timezone.utc) - timedelta(days=self.cycle_days)).isoformat()
        all_recent = self.store.list_recent(limit=200)
        sessions = [s for s in all_recent if s.created_at >= cutoff]

        if not sessions:
            notes.append("No sessions found in the cycle window.")
            logger.info("Curator: no sessions in window, skipping cycle.")
            return {
                "accepted": 0,
                "rejected": 0,
                "pending": 0,
                "cycle_ts": cycle_ts,
                "sessions_scanned": 0,
                "notes": notes,
            }

        notes.append(f"Scanned {len(sessions)} sessions from the last {self.cycle_days} days.")

        # 2. Extract patterns
        patterns = self._extractor.extract(sessions)
        notes.append(f"Extracted {len(patterns)} patterns.")

        # 3. Classify and process skill candidates
        skill_candidates = [p for p in patterns if p["type"] == "skill_candidate"]
        accepted = 0
        rejected = 0

        for candidate in skill_candidates:
            confidence = candidate["confidence"]

            if confidence >= self.accept_threshold and accepted < self.max_accepted:
                accepted += 1
                self._accept_candidate(candidate, cycle_ts)
            else:
                rejected += 1

        # 4. Log cycle results
        pending = max(0, len(skill_candidates) - accepted - rejected)

        result = {
            "accepted": accepted,
            "rejected": rejected,
            "pending": pending,
            "cycle_ts": cycle_ts,
            "sessions_scanned": len(sessions),
            "patterns_found": len(patterns),
            "skill_candidates": len(skill_candidates),
            "threshold": self.accept_threshold,
            "notes": notes,
        }

        logger.info(
            "Curator cycle complete: accepted=%d rejected=%d pending=%d",
            accepted,
            rejected,
            pending,
        )
        return result

    def _accept_candidate(self, candidate: dict, cycle_ts: str) -> Path:
        """Accept a skill candidate and write its manifest to disk."""
        detail = candidate["detail"]
        skill_name = detail.get("proposed_skill_name", "learned-skill")
        skill_dir = self.learned_skills_dir / skill_name
        skill_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "name": skill_name,
            "version": "0.1.0",
            "kind": "skill",
            "description": candidate.get("description", "Auto-learned skill from session patterns"),
            "description_zh": f"从会话模式自动学习的技能: {skill_name}",
            "backend": "llm",
            "tools": ["Read", "Write", "Bash", "Grep", "Glob"],
            "paired_skills": [],
            "script_path": None,
            "requires_layer": [],
            "system_prompt": self._make_system_prompt(candidate),
            "output_schema": {},
            "gates": [],
            "tags": ["auto-learned", f"confidence-{candidate['confidence']:.0%}"],
            "deprecated": False,
            "source": {
                "type": "curator-auto-learned",
                "cycle_ts": cycle_ts,
                "confidence": candidate["confidence"],
                "evidence_count": len(candidate.get("evidence", [])),
                **detail,
            },
        }

        manifest_path = skill_dir / "manifest.yaml"
        manifest_path.write_text(_to_yaml(manifest), encoding="utf-8")
        logger.info("Curator accepted skill: %s (confidence=%.2f)", skill_name, candidate["confidence"])
        return manifest_path

    @staticmethod
    def _make_system_prompt(candidate: dict) -> str:
        detail = candidate.get("detail", {})
        steps = detail.get("steps", [])
        agents = detail.get("agents", [])
        source = detail.get("source", "unknown")
        target = detail.get("target", "")

        lines = [
            f"# Auto-Learned Skill: {detail.get('proposed_skill_name', 'learned-skill')}",
            "",
            f"> Generated by Curator on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            f"> Source: {source}",
            f"> Confidence: {candidate.get('confidence', 0):.0%}",
            "",
        ]

        if target:
            lines.append(f"## Target Context")
            lines.append(f"")
            lines.append(f"Target: {target}")
            lines.append("")

        if agents:
            lines.append("## Agent Sequence")
            lines.append("")
            lines.append(" -> ".join(agents))
            lines.append("")

        if steps:
            lines.append("## Steps")
            lines.append("")
            for step in steps:
                lines.append(step)
            lines.append("")

        lines.append("## Notes")
        lines.append("")
        lines.append("- This skill was auto-learned by the Curator. Review and refine before production use.")
        lines.append("- Pinned skills bypass auto-archival.")

        return "\n".join(lines)


def _to_yaml(data: dict, indent: int = 0) -> str:
    """Minimal YAML serializer for manifest output.

    Avoids the pyyaml dependency for simple nested dicts.
    """
    lines: list[str] = []
    prefix = "  " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_to_yaml(value, indent + 1))
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
            elif all(isinstance(x, str) and len(x) < 60 for x in value):
                lines.append(f"{prefix}{key}: [{', '.join(value)}]")
            else:
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  - " + _to_yaml_inline(item))
                    else:
                        lines.append(f"{prefix}  - {item}")
        elif isinstance(value, str) and "\n" in value:
            lines.append(f"{prefix}{key}: |")
            for sub_line in value.split("\n"):
                lines.append(f"{prefix}  {sub_line}")
        elif isinstance(value, str):
            # Quote strings that could be ambiguous
            if value.startswith(("{", "[", "&", "*", "!", "|", ">", "%", "@", "`")) or value in (
                "true", "false", "null", "yes", "no", "on", "off",
            ):
                lines.append(f'{prefix}{key}: "{value}"')
            else:
                lines.append(f"{prefix}{key}: {value}")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif value is None:
            lines.append(f"{prefix}{key}: null")
        elif isinstance(value, float):
            lines.append(f"{prefix}{key}: {value}")
        else:
            lines.append(f"{prefix}{key}: {value}")

    return "\n".join(lines)


def _to_yaml_inline(data: dict) -> str:
    """Inline dict for YAML list items."""
    parts = [f"{k}: {v}" for k, v in data.items() if not isinstance(v, (dict, list))]
    return "{" + ", ".join(parts) + "}"
