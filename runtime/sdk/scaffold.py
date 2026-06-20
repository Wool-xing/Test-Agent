"""scaffold: create a new Skill from template."""

from __future__ import annotations

import re
from pathlib import Path

_SKILL_MD_TEMPLATE = """---
name: {name}
version: 0.1.0
display_name: {display_name}
description: {description}
permissions:
  network: none
  filesystem: read
  shell: none
  timeout: 30
---

# {display_name}

## Overview
{description}

## Quick Start

```bash
tagent skill install {name}
tagent "run {name} check"
```

## Input Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| target | string | yes | - | Target to check |

## Output Format

```json
{{
  "status": "pass",
  "summary": "Check completed",
  "details": {{}}
}}
```
"""

_EXECUTOR_STUB = '''"""Executor for {name} Skill."""

from __future__ import annotations


def execute(params: dict, ctx: dict | None = None) -> dict:
    """Execute the {name} skill check.

    Args:
        params: Input parameters matching SKILL.md schema.
        ctx: Execution context (config, trace_id, sandbox, etc.)

    Returns:
        Result dict with status, summary, details, checks, error.
    """
    target = params.get("target", "")
    if not target:
        return {{
            "status": "error",
            "summary": "No target provided",
            "details": {{}},
            "checks": [],
            "error": "Missing required parameter: target",
        }}

    # TODO: implement actual check logic
    return {{
        "status": "pass",
        "summary": f"{{target}} check completed (stub)",
        "details": {{"target": target}},
        "checks": [{{"name": "stub", "expected": "pass", "actual": "pass", "pass": True}}],
        "error": None,
    }}
'''

_VALID_NAME = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$')


def scaffold_skill(name: str, *, base_dir: Path | None = None) -> Path:
    """Create a new Skill directory with SKILL.md and executor.py stub.

    Args:
        name: Skill name in kebab-case (e.g. 'my-http-check').
        base_dir: Parent directory. Defaults to current working directory.

    Returns:
        Path to the created skill directory.

    Raises:
        ValueError: If name is not valid kebab-case.
    """
    if not _VALID_NAME.match(name):
        raise ValueError(
            f"Invalid skill name '{name}'. "
            f"Must be kebab-case: lowercase letters, digits, and hyphens "
            f"(e.g. 'my-http-check')."
        )

    base = Path(base_dir) if base_dir else Path.cwd()
    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    display_name = name.replace("-", " ").title()
    description = f"Check {display_name} status"

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        _SKILL_MD_TEMPLATE.format(name=name, display_name=display_name, description=description),
        encoding="utf-8",
    )

    executor = skill_dir / "executor.py"
    executor.write_text(_EXECUTOR_STUB.format(name=name), encoding="utf-8")

    return skill_dir
