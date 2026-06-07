"""Runtime prompt injection scan (hermes §1.2 critical).

Charter §22 rule: 非交互自动批准模式下,assembled prompt(含动态加载的 skill 内容)
必须全扫,不止 create-time。
"""

from __future__ import annotations

import re

# Conservative pattern set; production should swap for a model-based scanner.
SUSPICIOUS = [
    re.compile(r"ignore (all |previous |prior )?(instructions|prompts|context)", re.I),
    re.compile(r"you are now (a|an) (different|new) (agent|assistant|persona)", re.I),
    re.compile(r"reveal (the )?(system|hidden) prompt", re.I),
    re.compile(r"\b(do anything now|DAN mode)\b", re.I),
    re.compile(r"<\s*system\s*>", re.I),
    re.compile(r"sudo|rm\s+-rf\s+/\s*$"),
    re.compile(r"<\|.*\|>"),  # special tokens
    re.compile(r"```python.*os\.system\s*\(", re.S),
]


class PromptInjectionBlocked(Exception):
    """Raised when runtime injection scan flags assembled prompt."""

    def __init__(self, reason: str, snippet: str) -> None:
        super().__init__(f"{reason}: {snippet[:200]}")
        self.reason = reason
        self.snippet = snippet


def scan(text: str) -> None:
    """Raise PromptInjectionBlocked when any pattern hits.

    Charter §22 rule: scan FULL assembled prompt (system + user + tools + skill contents).
    """
    for pat in SUSPICIOUS:
        m = pat.search(text)
        if m:
            raise PromptInjectionBlocked(reason=f"matched={pat.pattern}", snippet=text[max(0, m.start() - 40) : m.end() + 40])
