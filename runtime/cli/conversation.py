"""Multi-turn conversation memory for interactive REPL.

Sliding-window message store. In-memory with optional JSON persistence.
Injects conversation context into LLM prompts for multi-turn awareness.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str
    ts: float = field(default_factory=time.time)


class ConversationMemory:
    """Sliding-window conversation store.

    Keeps last N turns + enforces character budget.
    Context is prepended to new user input for multi-turn LLM calls.
    """

    def __init__(
        self,
        session_id: str | None = None,
        max_turns: int = 20,
        max_chars: int = 8000,
    ):
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.max_turns = max_turns
        self.max_chars = max_chars
        self._messages: list[Message] = []

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    def add(self, role: str, content: str) -> None:
        """Append a message turn, truncating if over budget."""
        self._messages.append(Message(role=role, content=content))
        self._truncate()

    def build_context(self, current_input: str) -> str:
        """Build context string for LLM prompt.

        If no history, returns current_input unchanged.
        Otherwise wraps history + current input with clear markers.
        """
        if not self._messages:
            return current_input

        lines = ["Previous conversation:"]
        for m in self._messages:
            label = "User" if m.role == "user" else "Assistant"
            # Truncate long assistant messages to keep context tight
            text = m.content if len(m.content) <= 500 else m.content[:497] + "..."
            lines.append(f"[{label}]: {text}")

        lines.append("")
        lines.append(f"Current request: {current_input}")
        return "\n".join(lines)

    def clear(self) -> None:
        """Reset memory, keep session_id."""
        self._messages.clear()

    def dump(self, path: Path) -> None:
        """Persist to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "session_id": self.session_id,
            "max_turns": self.max_turns,
            "max_chars": self.max_chars,
            "messages": [
                {"role": m.role, "content": m.content, "ts": m.ts}
                for m in self._messages
            ],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> ConversationMemory:
        """Restore from JSON file. Returns fresh instance if file missing or corrupt."""
        if not path.is_file():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            max_chars = min(int(data.get("max_chars", 8000)), 32000)  # cap
            mem = cls(
                session_id=str(data.get("session_id", ""))[:64],
                max_turns=min(int(data.get("max_turns", 20)), 100),
                max_chars=max_chars,
            )
            for m in data.get("messages", []):
                role = str(m.get("role", ""))
                if role not in ("user", "assistant"):
                    continue  # skip malformed entries
                content = str(m.get("content", ""))[:max_chars]
                if not content.strip():
                    continue
                mem._messages.append(Message(role=role, content=content, ts=float(m.get("ts", 0))))
            mem._truncate()  # re-enforce budget after load
            return mem
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return cls()

    def _truncate(self) -> None:
        """Enforce max_turns and max_chars."""
        while len(self._messages) > self.max_turns:
            self._messages.pop(0)
        while self._total_chars() > self.max_chars and len(self._messages) > 1:
            self._messages.pop(0)

    def _total_chars(self) -> int:
        return sum(len(m.content) for m in self._messages)
