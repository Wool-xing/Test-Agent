"""TDD tests for Dependency Injection + Fakes (§补-25)."""

from runtime.infra.di import (
    ExecutionContext,
    FakeLLM,
    InMemoryStorage,
    InMemoryFS,
    FakeClock,
    RealFS,
    RealClock,
)


class TestFakeLLM:
    def test_fake_llm_returns_deterministic(self):
        """FakeLLM should return deterministic JSON responses."""
        llm = FakeLLM({"test": '{"ok": true}'})
        result = llm.complete_json("system", "test")
        assert result == {"ok": True}

    def test_fake_llm_tracks_calls(self):
        """FakeLLM should track all calls for verification."""
        llm = FakeLLM()
        llm.complete("system", "hello world")
        assert len(llm.calls) == 1
        assert llm.calls[0] == ("system", "hello world")

    def test_fake_llm_default_response(self):
        """FakeLLM should return default status response."""
        llm = FakeLLM()
        result = llm.complete_json("system", "unknown query")
        assert result == {"status": "ok"}


class TestInMemoryFS:
    def test_read_write(self):
        """InMemoryFS should read back what was written."""
        fs = InMemoryFS()
        fs.write_text("/tmp/test.txt", "hello")
        assert fs.read_text("/tmp/test.txt") == "hello"

    def test_exists(self):
        """InMemoryFS should report file existence."""
        fs = InMemoryFS({"existing.txt": "data"})
        assert fs.exists("existing.txt") is True
        assert fs.exists("missing.txt") is False

    def test_tracks_writes(self):
        """InMemoryFS should track all writes."""
        fs = InMemoryFS()
        fs.write_text("a.txt", "A")
        fs.write_text("b.txt", "B")
        assert len(fs.writes) == 2


class TestFakeClock:
    def test_advance_time(self):
        """FakeClock should allow manual time advancement."""
        clock = FakeClock(1000.0)
        assert clock.now() == 1000.0
        clock.advance(60.0)
        assert clock.now() == 1060.0

    def test_tracks_sleeps(self):
        """FakeClock should track sleep calls."""
        clock = FakeClock()
        clock.sleep(5.0)
        assert clock.sleeps == [5.0]


class TestExecutionContext:
    def test_context_with_fakes(self):
        """ExecutionContext should accept injected dependencies."""
        llm = FakeLLM()
        fs = InMemoryFS()
        ctx = ExecutionContext(trace_id="test-001", llm=llm, fs=fs)
        assert ctx.trace_id == "test-001"
        assert ctx.llm is llm
        assert ctx.fs is fs

    def test_context_defaults(self):
        """ExecutionContext should have None defaults."""
        ctx = ExecutionContext()
        assert ctx.llm is None
        assert ctx.storage is None
