"""Permission Manager — 3-level allow/deny/ask with console confirmation.

§四-A 原则2, Sprint 2 P1-004: 分级权限 + 用户确认 + TUI内交互确认.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class PermissionLevel(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionRule:
    pattern: str          # glob pattern: "Bash(rm *)", "Write(**/*.env)"
    level: PermissionLevel


@dataclass
class PermissionDecision:
    allowed: bool
    level: PermissionLevel
    reason: str = ""


# Confirmation callback — injected by UI layer (Rich/Textual)
_confirm_fn: Callable[[str, str], bool] | None = None


def set_confirm_callback(fn: Callable[[str, str], bool]) -> None:
    """Inject UI-specific confirmation function (Rich prompt, Textual dialog, etc.)."""
    global _confirm_fn
    _confirm_fn = fn


# Default confirmation using Rich console
def _rich_confirm(operation: str, target: str) -> bool:
    """Default: Rich console Yes/No prompt."""
    from rich.prompt import Confirm
    return Confirm.ask(
        f"[yellow]Allow '{operation}' on '{target}'?[/]",
        default=False,
    )


# Built-in deny rules for destructive operations
_DENY_PATTERNS = [
    "Bash(rm -rf /*)",
    "Bash(sudo *)",
    "Write(.env)",
    "Write(*.env)",
    "Write(**/*.env)",
    "Write(**/id_rsa*)",
    "Bash(:(){ :|:& };:)",
    "Write(/etc/*)",
    "Write(/proc/*)",
]

# Built-in allow rules for safe operations
_ALLOW_PATTERNS = [
    "Read(**/*.py)",
    "Read(**/*.md)",
    "Write(workspace/**)",
    "Bash(echo *)",
    "Bash(ls *)",
    "Bash(git *)",
    "Bash(python *)",
    "Bash(pytest *)",
]


class PermissionManager:
    """3-level permission system with pattern matching."""

    def __init__(self):
        self._rules: list[PermissionRule] = []
        # Load built-in rules
        for p in _DENY_PATTERNS:
            self._rules.append(PermissionRule(p, PermissionLevel.DENY))
        for p in _ALLOW_PATTERNS:
            self._rules.append(PermissionRule(p, PermissionLevel.ALLOW))

    def add_rule(self, pattern: str, level: PermissionLevel) -> None:
        """Add a custom permission rule."""
        self._rules.append(PermissionRule(pattern, level))

    def check(self, operation: str, target: str) -> PermissionDecision:
        """Check if operation on target is allowed. Returns PermissionDecision."""
        full = f"{operation}({target})"

        # Check DENY rules first (most restrictive)
        for rule in self._rules:
            if rule.level == PermissionLevel.DENY and _match_pattern(full, rule.pattern):
                return PermissionDecision(allowed=False, level=PermissionLevel.DENY,
                                         reason=f"blocked by rule: {rule.pattern}")

        # Check ALLOW rules
        for rule in self._rules:
            if rule.level == PermissionLevel.ALLOW and _match_pattern(full, rule.pattern):
                return PermissionDecision(allowed=True, level=PermissionLevel.ALLOW)

        # Default: ASK — use UI confirmation
        confirm = _confirm_fn or _rich_confirm
        if confirm(operation, target):
            return PermissionDecision(allowed=True, level=PermissionLevel.ASK, reason="user confirmed")
        return PermissionDecision(allowed=False, level=PermissionLevel.ASK, reason="user denied")

    def check_destructive(self, command: str) -> bool:
        """Quick check: is this command potentially destructive? Returns True if risky."""
        dangerous = ["rm ", "sudo ", "chmod ", "chown ", "dd ", "mkfs.", ":(){", "> /dev/"]
        return any(d in command for d in dangerous)


# Singleton
_manager: PermissionManager | None = None


def get_permission_manager() -> PermissionManager:
    global _manager
    if _manager is None:
        _manager = PermissionManager()
    return _manager


def _match_pattern(text: str, pattern: str) -> bool:
    """Simple glob-style pattern matching with * wildcard."""
    import fnmatch
    return fnmatch.fnmatch(text, pattern)
