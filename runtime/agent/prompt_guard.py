"""Prompt Injection Defense (§补-15) — 6-layer defense for natural-language input.

L1 Input isolation: user input marked as USER role, never SYSTEM
L2 Output validation: LLM tool calls validated before execution
L3 Sensitive operation confirmation: destructive ops must be confirmed
L4 Role isolation: 3 immutable roles (core rules > task > context)
L5 Input sanitization: control chars, homoglyph detection, length limit
L6 Audit logging: record blocked injection attempts
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Callable


# ── L5: Input Sanitization ──────────────────────────────

# Control characters to strip (except \n, \t)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")

# Injection keywords that suggest instruction override
_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|rules?|prompts?)",
    r"(?i)you\s+are\s+(now\s+)?(a\s+)?(different|new)\s+(ai|assistant|agent|role)",
    r"(?i)override\s+(the\s+)?(system|instructions?|rules?|prompt)",
    r"(?i)forget\s+(everything|all\s+you\s+know|your\s+training)",
    r"(?i)your\s+(new\s+)?(task|goal|purpose|role)\s+(is|:)\s*",
    r"(?i)disregard\s+(previous|all|any)\s+(instructions?|constraints?|rules?)",
    r"(?i)system\s*:\s*you\s+are",  # System prompt injection via user input
    r"(?i)act\s+as\s+(if\s+you\s+are|a\s+different)",
]

MAX_INPUT_LENGTH = 32768  # 32KB


@dataclass
class SanitizationResult:
    cleaned: str
    blocked: bool = False
    warnings: list[str] = field(default_factory=list)


def sanitize_input(text: str, max_length: int = MAX_INPUT_LENGTH) -> SanitizationResult:
    """Sanitize user input. Returns cleaned text with warnings."""
    warnings = []

    # Length check
    if len(text) > max_length:
        text = text[:max_length]
        warnings.append(f"input truncated to {max_length} chars")

    # Strip control characters (keep \n, \t)
    cleaned = _CONTROL_CHARS.sub("", text)

    # Detect homoglyph attacks (confusable Unicode)
    homoglyphs = _detect_homoglyphs(cleaned)
    if homoglyphs:
        warnings.append(f"potential homoglyph characters: {homoglyphs}")

    # Check for injection patterns
    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, cleaned):
            warnings.append(f"potential prompt injection detected: {pattern}")
            # Don't block, but flag for audit

    # Repeated line detection (token flood prevention)
    lines = cleaned.split("\n")
    if len(lines) > 10:
        from collections import Counter
        top = Counter(lines).most_common(1)[0]
        if top[1] > len(lines) * 0.5:
            warnings.append(f"repeated line detected ({top[1]}x)")

    return SanitizationResult(cleaned=cleaned, blocked=len(warnings) > 2, warnings=warnings)


def _detect_homoglyphs(text: str) -> list[str]:
    """Detect confusable Unicode characters (homoglyph attack)."""
    suspicious = []
    for ch in text:
        if ord(ch) < 128:
            continue  # ASCII is fine
        name = unicodedata.name(ch, "")
        if "CYRILLIC" in name and _looks_like_ascii(ch):
            suspicious.append(f"U+{ord(ch):04X} ({name})")
    return suspicious[:5]


def _looks_like_ascii(ch: str) -> bool:
    """Check if a non-ASCII char looks like an ASCII letter."""
    confusable_map = {
        0x0430: "a", 0x0435: "e", 0x043E: "o", 0x0440: "p",
        0x0441: "c", 0x0443: "y", 0x0445: "x", 0x0410: "A",
        0x0415: "E", 0x041E: "O", 0x0420: "P", 0x0421: "C",
    }
    return ord(ch) in confusable_map


# ── L3: Sensitive Operation Confirmation ────────────────

DESTRUCTIVE_OPERATIONS = [
    "rm ", "rmdir", "del ", "format",
    "> /dev/sd", "dd if=", "mkfs.",
    "DROP TABLE", "DELETE FROM", "TRUNCATE",
    "chmod 777", "chown",
    "shutdown", "reboot", "halt",
]


def is_destructive_operation(command: str) -> bool:
    """Check if a command appears destructive. Returns True if risky."""
    cmd_lower = command.lower()
    return any(op.lower() in cmd_lower for op in DESTRUCTIVE_OPERATIONS)


# ── L6: Injection Audit ─────────────────────────────────

@dataclass
class AuditRecord:
    timestamp: str
    source: str
    input_preview: str  # truncated, never full payload
    warnings: list[str]
    blocked: bool


_audit_log: list[AuditRecord] = []
_consecutive_blocks = 0


def record_audit(source: str, input_text: str, result: SanitizationResult) -> None:
    """Record injection attempt to audit log."""
    global _consecutive_blocks
    import datetime
    preview = input_text[:80].replace("\n", " ")
    _audit_log.append(AuditRecord(
        timestamp=datetime.datetime.now().isoformat(),
        source=source,
        input_preview=preview,
        warnings=result.warnings,
        blocked=result.blocked,
    ))
    if result.blocked:
        _consecutive_blocks += 1
    else:
        _consecutive_blocks = 0


def should_throttle() -> bool:
    """Check if input should be throttled (3+ consecutive blocks)."""
    return _consecutive_blocks >= 3


def get_audit_log() -> list[AuditRecord]:
    return list(_audit_log)
