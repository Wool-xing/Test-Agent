"""Multi-turn conversation memory for interactive REPL.

Sliding-window message store. In-memory with optional JSON persistence.
Injects conversation context into LLM prompts for multi-turn awareness.

Includes MEMORY.md support for cross-session persistent knowledge.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

# MEMORY.md path — shared across all sessions
_MEMORY_FILE = Path(__file__).resolve().parents[2] / "workspace" / "gateway" / "MEMORY.md"
_MEMORY_LOCK = threading.Lock()
_MEMORY_MAX_CHARS = 2000  # cap injected memory to prevent prompt injection / context bloat

# Project context files — auto-discovered from cwd upward
_PROJECT_CONTEXT_FILES = ["CLAUDE.md", "AGENTS.md", ".claude/CLAUDE.md"]
_PROJECT_CONTEXT_CACHE: str | None = None


def _discover_project_context() -> str | None:
    """Walk cwd upward looking for context files. Cached after first call."""
    global _PROJECT_CONTEXT_CACHE
    if _PROJECT_CONTEXT_CACHE is not None:
        return _PROJECT_CONTEXT_CACHE or None
    cwd = Path.cwd()
    for d in [cwd, *cwd.parents]:
        for name in _PROJECT_CONTEXT_FILES:
            cf = d / name
            if cf.is_file():
                try:
                    content = cf.read_text(encoding="utf-8", errors="replace")
                    _PROJECT_CONTEXT_CACHE = content[:4000]  # cap
                    logger.info("project context loaded: {}", cf)
                    return _PROJECT_CONTEXT_CACHE
                except OSError:
                    continue
        if (d / ".git").is_dir():
            break  # stop at repo root
    _PROJECT_CONTEXT_CACHE = ""
    return None


@dataclass
class Message:
    role: str  # "user" | "assistant"
    content: str
    ts: float = field(default_factory=time.time)


def load_memory_md() -> str:
    """Read MEMORY.md content. Returns empty string if file missing."""
    if not _MEMORY_FILE.is_file():
        return ""
    try:
        content = _MEMORY_FILE.read_text(encoding="utf-8").strip()
        # Cap to prevent context overflow
        return content[:_MEMORY_MAX_CHARS] if len(content) > _MEMORY_MAX_CHARS else content
    except PermissionError:
        logger.warning("MEMORY.md read permission denied: {}", _MEMORY_FILE)
        return ""
    except OSError as e:
        logger.warning("MEMORY.md read error: {}", e)
        return ""


def save_memory_fact(fact: str) -> None:
    """Append a fact to MEMORY.md. Creates file if missing.

    Sanitizes input: strips newlines to prevent injection, caps length.
    Thread-safe via lock to prevent TOCTOU races.
    """
    # Sanitize: strip newlines to prevent injection, cap length
    sanitized = fact.strip().replace("\n", " ").replace("\r", " ")[:200]
    if not sanitized:
        return
    line = f"- {sanitized}"

    with _MEMORY_LOCK:
        _MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        existing = load_memory_md()
        # Avoid duplicate facts
        if line in existing:
            return
        new_content = (existing + "\n" + line).strip() if existing else line
        try:
            _MEMORY_FILE.write_text(new_content + "\n", encoding="utf-8")
        except OSError as e:
            logger.warning("MEMORY.md write error: {}", e)


def forget_memory_fact(keyword: str) -> int:
    """Remove lines containing keyword from MEMORY.md. Returns count removed.

    Requires minimum 3-char keyword to avoid accidental mass deletion.
    Thread-safe via lock.
    """
    keyword = keyword.strip()
    if len(keyword) < 3:
        return 0

    with _MEMORY_LOCK:
        if not _MEMORY_FILE.is_file():
            return 0
        try:
            lines = _MEMORY_FILE.read_text(encoding="utf-8").splitlines()
        except OSError as e:
            logger.warning("MEMORY.md read error: {}", e)
            return 0
        kept = [l for l in lines if keyword.lower() not in l.lower()]
        removed = len(lines) - len(kept)
        if removed > 0:
            try:
                _MEMORY_FILE.write_text("\n".join(kept).strip() + ("\n" if kept else ""), encoding="utf-8")
            except OSError as e:
                logger.warning("MEMORY.md write error: {}", e)
                return 0
        return removed


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

        Layers (in order): project context → MEMORY.md → conversation history → current input.
        All sourced from delimited blocks to prevent prompt injection.
        """
        parts: list[str] = []

        # Layer 0: Project context (CLAUDE.md / AGENTS.md auto-discovered)
        proj_ctx = _discover_project_context()
        if proj_ctx:
            parts.append("Project context (from workspace):")
            parts.append("```project")
            parts.append(proj_ctx)
            parts.append("```")
            parts.append("")

        # Layer 1: Cross-session persistent memory (delimited to prevent prompt injection)
        mem_md = load_memory_md()
        if mem_md:
            parts.append("Persistent knowledge (from MEMORY.md):")
            parts.append("```memory")
            parts.append(mem_md)
            parts.append("```")
            parts.append("")

        # Layer 2: Conversation history
        if self._messages:
            parts.append("Previous conversation:")
            for m in self._messages:
                label = "User" if m.role == "user" else "Assistant"
                # Truncate long assistant messages to keep context tight
                text = m.content if len(m.content) <= 500 else m.content[:497] + "..."
                parts.append(f"[{label}]: {text}")
            parts.append("")

        # Layer 3: Current request
        parts.append(f"Current request: {current_input}")
        return "\n".join(parts)

    def clear(self) -> None:
        """Reset memory, keep session_id."""
        self._messages.clear()

    def undo_last_exchange(self) -> tuple[str | None, str | None]:
        """Remove last user+assistant exchange. Returns (user_text, assistant_text)."""
        assistant = None
        user = None
        if self._messages and self._messages[-1].role == "assistant":
            assistant = self._messages.pop().content
        if self._messages and self._messages[-1].role == "user":
            user = self._messages.pop().content
        return user, assistant

    def last_user_message(self) -> str | None:
        """Return the last user message content, or None."""
        for m in reversed(self._messages):
            if m.role == "user":
                return m.content
        return None

    def dump(self, path: Path) -> None:
        """Persist to JSON file. Also indexes in FTS5 for full-text search."""
        path.parent.mkdir(parents=True, exist_ok=True)
        # Index messages for full-text search (P3 #16)
        try:
            from runtime.cli.search import index_message
            for m in self._messages:
                index_message(self.session_id, m.role, m.content, str(m.ts))
        except Exception:
            pass  # search indexing is best-effort
        data = {
            "session_id": self.session_id,
            "max_turns": self.max_turns,
            "max_chars": self.max_chars,
            "messages": [
                {"role": m.role, "content": m.content, "ts": m.ts}
                for m in self._messages
            ],
        }
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as e:
            logger.warning("conversation dump failed for {}: {}", path, e)

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
        """Enforce max_turns and max_chars. Auto-compacts before dropping."""
        # Auto-compact turn budget overflow
        overflow = len(self._messages) - self.max_turns
        if overflow > 0:
            self._auto_compact(overflow)

        # Compact char budget overflow (with safety limit to prevent infinite loop)
        for _ in range(10):  # max 10 iterations
            if self._total_chars() <= self.max_chars or len(self._messages) <= 1:
                break
            # Pop oldest messages until under budget
            dropped: list[Message] = []
            while self._total_chars() > self.max_chars and len(self._messages) > 1:
                dropped.append(self._messages.pop(0))
            # Insert summary (capped to avoid re-exceeding budget)
            if dropped:
                summary = self._build_summary(dropped)[:500]
                self._messages.insert(0, Message(role="assistant", content=summary))

    def _auto_compact(self, overflow: int) -> None:
        """Compress oldest turns to stay within max_turns budget."""
        if overflow <= 0 or not self._messages:
            return
        count = min(overflow, len(self._messages))
        dropped = [self._messages.pop(0) for _ in range(count)]
        if dropped:
            summary = self._build_summary(dropped)[:500]
            self._messages.insert(0, Message(role="assistant", content=summary))

    @staticmethod
    def _build_summary(messages: list[Message]) -> str:
        """Build a concise summary of dropped conversation turns."""
        parts: list[str] = []
        for m in messages[:20]:
            role = "Q" if m.role == "user" else "A"
            text = m.content[:80] + "..." if len(m.content) > 80 else m.content
            parts.append(f"[{role}] {text}")
        return f"[Compacted {len(messages)} turns]\n" + "\n".join(parts[:15])

    def _total_chars(self) -> int:
        return sum(len(m.content) for m in self._messages)
