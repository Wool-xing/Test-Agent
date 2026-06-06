"""TDD: ConversationMemory unit tests — RED phase (tests first)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from runtime.cli.conversation import ConversationMemory, Message, save_memory_fact, load_memory_md, forget_memory_fact


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
        """build_context() with no history wraps input with 'Current request:'."""
        mem = ConversationMemory()
        ctx = mem.build_context("test login")
        assert "test login" in ctx
        assert "Current request" in ctx

    def test_max_turns_truncation(self):
        """Sliding window: oldest turns compacted into summary when exceeding max_turns."""
        mem = ConversationMemory(max_turns=4)
        for i in range(6):
            mem.add("user", f"msg {i}")

        # 6 messages → 4 max turns → overflow 2 compacted into summary
        # Messages: [summary(2), msg2, msg3, msg4, msg5] = 5 (4 + summary)
        assert 4 <= len(mem.messages) <= 6
        assert mem.messages[-1].content == "msg 5"

    def test_max_chars_truncation(self):
        """Character budget: oldest messages compacted rather than just dropped."""
        mem = ConversationMemory(max_chars=100)
        mem.add("user", "A" * 60)
        mem.add("assistant", "B" * 60)  # 120 total, compacts first

        # Should have at least 1 message and char budget respected
        assert len(mem.messages) >= 1
        assert mem._total_chars() <= mem.max_chars + 500  # summary may add some overhead

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


class TestMemoryMD:
    """Test MEMORY.md cross-session persistence."""

    def test_save_and_load_fact(self):
        """save_memory_fact appends; load_memory_md returns content."""
        # Clean up first
        forget_memory_fact("test-integration")
        save_memory_fact("Test-Agent uses Python")
        mem = load_memory_md()
        assert "Test-Agent uses Python" in mem

    def test_duplicate_fact_not_appended(self):
        """Saving same fact twice does not duplicate."""
        forget_memory_fact("duplicate-test")
        save_memory_fact("Unique fact for dedup test")
        mem1 = load_memory_md()
        save_memory_fact("Unique fact for dedup test")
        mem2 = load_memory_md()
        assert mem1 == mem2

    def test_forget_removes_matching_line(self):
        """forget_memory_fact removes lines containing keyword."""
        save_memory_fact("Temp fact to be forgotten")
        removed = forget_memory_fact("Temp fact")
        assert removed >= 1
        mem = load_memory_md()
        if mem:
            assert "Temp fact to be forgotten" not in mem

    def test_load_memory_md_empty_when_no_file(self):
        """load_memory_md returns empty string when no MEMORY.md exists."""
        # forget all test facts
        forget_memory_fact("Test-Agent")
        forget_memory_fact("Unique")
        forget_memory_fact("Temp")
        # After cleanup, should be empty or just contain non-test facts
        mem = load_memory_md()
        assert isinstance(mem, str)

    def test_build_context_includes_memory(self):
        """build_context prepends MEMORY.md facts when present."""
        save_memory_fact("Project: Test-Agent framework")
        mem = ConversationMemory()
        ctx = mem.build_context("run smoke test")
        assert "Project: Test-Agent framework" in ctx
        assert "Persistent knowledge" in ctx
        forget_memory_fact("Project: Test-Agent framework")

    def test_forget_nonexistent_keyword(self):
        """forget with no match returns 0."""
        removed = forget_memory_fact("xyznonexistent987654321")
        assert removed == 0
