"""TDD: ConversationMemory unit tests — RED phase (tests first)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from runtime.cli.conversation import ConversationMemory, Message


class TestConversationMemory:
    """Test ConversationMemory: add, truncate, context, dump/load, clear."""

    def test_add_and_retrieve_messages(self):
        """add() stores messages; messages property returns them."""
        mem = ConversationMemory()
        mem.add("user", "test the login page")
        mem.add("assistant", "routing to requirements-analyst...")

        assert len(mem.messages) == 2
        assert mem.messages[0].role == "user"
        assert mem.messages[0].content == "test the login page"
        assert mem.messages[1].role == "assistant"

    def test_build_context_wraps_history(self):
        """build_context() formats history + current input for the LLM prompt."""
        mem = ConversationMemory()
        mem.add("user", "test login")
        mem.add("assistant", "done, found 2 bugs")

        ctx = mem.build_context("also test register")
        assert "test login" in ctx
        assert "done, found 2 bugs" in ctx
        assert "also test register" in ctx
        assert "Previous conversation" in ctx

    def test_build_context_empty_memory(self):
        """build_context() with no history returns just the current input."""
        mem = ConversationMemory()
        ctx = mem.build_context("test login")
        assert ctx == "test login"

    def test_max_turns_truncation(self):
        """Sliding window: oldest messages dropped when exceeding max_turns."""
        mem = ConversationMemory(max_turns=4)
        for i in range(6):
            mem.add("user", f"msg {i}")

        assert len(mem.messages) == 4
        assert mem.messages[0].content == "msg 2"
        assert mem.messages[-1].content == "msg 5"

    def test_max_chars_truncation(self):
        """Character budget: oldest messages dropped until under limit."""
        mem = ConversationMemory(max_chars=100)
        mem.add("user", "A" * 60)
        mem.add("assistant", "B" * 60)  # 120 total, drops first

        assert len(mem.messages) == 1
        assert mem.messages[0].content == "B" * 60

    def test_dump_and_load_roundtrip(self):
        """dump() writes JSON; load() restores identical state."""
        mem = ConversationMemory(session_id="test-123")
        mem.add("user", "hello")
        mem.add("assistant", "hi there")

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "session.json"
            mem.dump(path)

            restored = ConversationMemory.load(path)
            assert restored.session_id == "test-123"
            assert len(restored.messages) == 2
            assert restored.messages[0].content == "hello"

    def test_load_nonexistent_file(self):
        """load() on missing file returns fresh ConversationMemory."""
        mem = ConversationMemory.load(Path("/nonexistent/path.json"))
        assert len(mem.messages) == 0
        assert mem.session_id != ""

    def test_clear_resets_memory(self):
        """clear() removes all messages, keeps session_id."""
        mem = ConversationMemory(session_id="keep-me")
        mem.add("user", "something")
        mem.clear()

        assert len(mem.messages) == 0
        assert mem.session_id == "keep-me"

    def test_message_dataclass(self):
        """Message stores role, content, and auto-generates timestamp."""
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"
        assert msg.ts is not None
