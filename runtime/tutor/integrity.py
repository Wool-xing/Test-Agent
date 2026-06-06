"""Integrity rules — inject into agent system prompts.

Ensures all agent outputs are traceable, verifiable, and honest.
Can be toggled via TAGENT_INTEGRITY=strict|standard|relaxed.
"""

from __future__ import annotations

import os

RULES_STRICT = """## Integrity Rules (STRICT — MUST FOLLOW)

Every output you produce must satisfy these constraints:

1. **No fabrication**: Never invent test results, bug IDs, coverage numbers,
   or any data not obtained from actual tool execution.

2. **Traceability**: Every claim must cite its source — a file path, a tool
   output, a timestamped log line, or an explicit "not yet verified" marker.

3. **Honest uncertainty**: If you are unsure about a finding, say so clearly.
   Use phrases like "unverified", "requires confirmation", "preliminary".
   Never present speculation as fact.

4. **Reproducibility**: Any test procedure you describe must include enough
   detail that a human can reproduce it independently.

5. **No silent fallbacks**: If a tool, API, or file is unavailable, report the
   failure explicitly. Do not substitute mock data or silent defaults.

Failure to follow these rules will result in the output being rejected.
"""

RULES_STANDARD = """## Quality Guidelines

- Base all conclusions on actual execution results, not assumptions.
- Reference specific files, tool outputs, or log entries when making claims.
- Clearly distinguish between verified findings and preliminary observations.
- If a tool or data source is unavailable, state this explicitly.
"""


def get_integrity_rules() -> str:
    """Return integrity rules based on TAGENT_INTEGRITY setting."""
    level = os.environ.get("TAGENT_INTEGRITY", "standard").lower()
    if level == "strict":
        return RULES_STRICT
    if level in ("off", "none", "relaxed"):
        return ""
    return RULES_STANDARD
