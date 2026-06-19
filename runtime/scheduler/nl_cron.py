"""Natural language → cron expression parser.

Converts human descriptions to croniter-compatible expressions.
No LLM needed — pattern matching covers the most common cases.
"""

from __future__ import annotations

import re

# Pattern: (regex, cron_expression_template)
_PATTERNS: list[tuple[str, str]] = [
    # Every N minutes/hours
    (r"every\s+(\d+)\s*min", "*/{n} * * * *"),
    (r"every\s+(\d+)\s*hour", "0 */{n} * * *"),
    # Specific times (single number after "at" = hour)
    (r"every\s+morning\s+(?:at\s+)?(\d+)", "0 {h} * * *"),
    (r"every\s+evening\s+(?:at\s+)?(\d+)", "0 {h} * * *"),
    (r"every\s+day\s+(?:at\s+)?(\d+)", "0 {h} * * *"),
    (r"every\s+night\s+(?:at\s+)?(\d+)", "0 {h} * * *"),
    (r"daily\s+(?:at\s+)?(\d+)", "0 {h} * * *"),
    # Daily with time (before plain daily)
    (r"(?:daily|every\s+day)\s+(?:at\s+)?(\d+)", "0 {h} * * *"),

    # Weekly (word boundary prevents month matching mon)
    (r"every\s+\b(mon|tue|wed|thu|fri|sat|sun)\b", "0 9 * * {d}"),
    (r"every\s+\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", "0 9 * * {d}"),
    # Monthly (specific day before default — but avoid matching "every monday" as "month")
    (r"every\s+month\s+(?:on\s*(?:day\s*)?)?(\d+)", "0 9 {d} * *"),
    (r"monthly\s+(?:on\s*(?:day\s*)?)?(\d+)", "0 9 {d} * *"),
    # Hourly
    (r"hourly", "0 * * * *"),
    (r"every\s+hour", "0 * * * *"),
    # Daily defaults
    (r"daily", "0 9 * * *"),
    (r"every\s+day", "0 9 * * *"),
    (r"every\s+morning", "0 8 * * *"),
    (r"every\s+evening", "0 20 * * *"),
    (r"every\s+night", "0 2 * * *"),
    # Weekly defaults
    (r"every\s+week", "0 9 * * 1"),
    (r"weekly", "0 9 * * 1"),
    # Monthly defaults
    (r"every\s+month", "0 9 1 * *"),
    (r"monthly", "0 9 1 * *"),
]

_DAY_MAP = {
    "mon": "1", "monday": "1",
    "tue": "2", "tuesday": "2",
    "wed": "3", "wednesday": "3",
    "thu": "4", "thursday": "4",
    "fri": "5", "friday": "5",
    "sat": "6", "saturday": "6",
    "sun": "0", "sunday": "0",
}

_HOUR_MAP = {
    "midnight": 0, "noon": 12,
}


def parse(text: str) -> str | None:
    """Convert natural language time description to cron expression.

    Examples:
        "every morning" → "0 8 * * *"
        "every day at 18" → "0 18 * * *"
        "every 30 min" → "*/30 * * * *"
        "every monday" → "0 9 * * 1"
        "hourly" → "0 * * * *"

    Returns None if no pattern matches.
    """
    text = text.lower().strip()

    # Handle "at 8am" / "at 18:00" patterns
    m = re.match(r"at\s+(\d{1,2})\s*(am|pm)?", text)
    if m:
        hour = int(m.group(1))
        if m.group(2) == "pm" and hour < 12:
            hour += 12
        return f"0 {hour} * * *"

    # Handle "every N minutes/hours at :MM" patterns
    m = re.match(r"every\s+(\d+)\s*min", text)
    if m:
        return f"*/{m.group(1)} * * * *"

    m = re.match(r"every\s+(\d+)\s*hour", text)
    if m:
        return f"0 */{m.group(1)} * * *"

    # General pattern matching
    for pattern, template in _PATTERNS:
        m = re.search(pattern, text)
        if not m:
            continue
        groups = [g for g in m.groups() if g is not None]
        # Build values: prefer template hints over heuristics
        values: dict[str, str] = {}
        for g in groups:
            g = str(g).lower()
            if g in _DAY_MAP:
                values["d"] = _DAY_MAP[g]
            elif g in _HOUR_MAP:
                values["h"] = str(_HOUR_MAP[g])
            elif g.isdigit():
                n = int(g)
                # Template-driven assignment: if template has {h}, prefer hour
                if template and "{h}" in template and n <= 23 and "h" not in values:
                    values["h"] = str(n)
                elif template and "{d}" in template and n <= 31 and "d" not in values:
                    values["d"] = str(n)
                elif n >= 24:
                    values["n"] = str(n)
                elif n <= 7 and "d" not in values:
                    values["d"] = str(n)
                else:
                    values["h"] = str(n)

        # Fill defaults
        values.setdefault("h", "9")
        values.setdefault("n", "1")
        values.setdefault("d", "*")

        if template is None:
            continue
        expr = template.format(**values)
        # Validate
        try:
            from datetime import datetime, timezone

            from croniter import croniter
            croniter(expr, datetime.now(timezone.utc))
            return expr
        except Exception:
            continue

    return None


def examples() -> list[str]:
    """Return list of example natural language inputs and their cron expressions."""
    return [
        "every morning    → 0 8 * * *",
        "every day at 18  → 0 18 * * *",
        "every 30 min     → */30 * * * *",
        "every monday     → 0 9 * * 1",
        "hourly           → 0 * * * *",
        "every month      → 0 9 1 * *",
        "at 8am           → 0 8 * * *",
        "every night      → 0 2 * * *",
    ]
