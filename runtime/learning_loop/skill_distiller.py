"""Skill distillation — auto-generate reusable skills from execution patterns.

After a complex multi-agent task, analyze the execution and offer to distill
the pattern into a reusable skill document (skills/*.md).

Core loop:
  1. Detect complex execution (≥3 DAG nodes, ≥2 different agent kinds)
  2. Extract the user's prompt + agent execution chain
  3. Generate a skill template with frontmatter + steps
  4. Offer via REPL: "Save this as a reusable skill?"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExecutionTrace:
    """Captured execution data for skill distillation."""
    user_prompt: str
    agent_chain: list[str] = field(default_factory=list)
    node_count: int = 0
    detected_platform: str = ""
    detected_qualities: list[str] = field(default_factory=list)

    @property
    def is_distillable(self) -> bool:
        """Complex enough to warrant a reusable skill."""
        unique_agents = len(set(self.agent_chain))
        return self.node_count >= 3 and unique_agents >= 2


def capture_trace(user_input: str, decision_summary: dict | None = None) -> ExecutionTrace:
    """Capture execution metadata for possible skill distillation."""
    trace = ExecutionTrace(user_prompt=user_input)
    if decision_summary:
        nodes = decision_summary.get("nodes", [])
        trace.node_count = len(nodes)
        trace.agent_chain = [n.get("name", n.get("kind", "?")) for n in nodes]
        trace.detected_platform = decision_summary.get("detected_target_type", "")
        trace.detected_qualities = decision_summary.get("detected_qualities", [])
    return trace


def suggest_skill_name(trace: ExecutionTrace) -> str:
    """Generate a reasonable skill name from the execution trace."""
    platform = trace.detected_platform.replace("-", " ").replace("_", " ")
    qualities = "-".join(trace.detected_qualities[:2]) if trace.detected_qualities else "test"

    if platform and qualities:
        return f"{qualities}-{platform.replace(' ', '-')}"
    if platform:
        return f"{platform.replace(' ', '-')}-test"
    return "custom-test"


def distill_skill(trace: ExecutionTrace, skill_name: str | None = None) -> str:
    """Generate a skill .md file content from execution trace.

    Returns the file path of the generated skill.
    """
    name = skill_name or suggest_skill_name(trace)
    skill_dir = Path(__file__).resolve().parents[2] / "skills"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / f"{name}.md"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    agent_list = "\n".join(f"  - {a}" for a in trace.agent_chain[:10])

    content = f"""---
name: {name}
description: "Auto-distilled skill from execution on {now}. Original prompt: {trace.user_prompt[:100]}"
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: script
---

# {name}

> Auto-generated from successful execution on {now}.

## Trigger

```text
/{name} [prompt]
```

## Original Task

{trace.user_prompt}

## Execution Chain

{agent_list}

## Steps

1. Analyze the request and route to appropriate agents
2. Execute the test workflow
3. Report results

## Notes

- This skill was auto-distilled. Edit to refine.
- See [skills/README.md](README.md) for conventions.
"""
    skill_path.write_text(content, encoding="utf-8")
    logger.info("skill distilled: %s", skill_path)
    return str(skill_path)
