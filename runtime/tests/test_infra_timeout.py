"""TDD tests for timeout hierarchy (§补-21)."""

import time

import pytest

from runtime.infra.timeout import (
    TimeoutConfig,
    TimeoutResult,
    get_timeout_config,
    run_with_timeout,
    set_timeout_config,
)


class TestTimeoutConfig:
    def test_default_config(self):
        """Default timeout config should have sane values."""
        cfg = get_timeout_config()
        assert cfg.session_idle == 1800
        assert cfg.llm_request == 120
        assert cfg.test_execution == 300

    def test_custom_config(self):
        """Custom config should override defaults."""
        old = get_timeout_config()
        try:
            cfg = TimeoutConfig(test_execution=60, shell_exec=10)
            set_timeout_config(cfg)
            assert get_timeout_config().test_execution == 60
        finally:
            set_timeout_config(old)

    def test_outer_exceeds_inner(self):
        """L0 session timeout should exceed L3 test timeout."""
        cfg = get_timeout_config()
        assert cfg.session_idle >= cfg.test_execution


class TestRunWithTimeout:
    def test_fast_completion(self):
        """Fast function should complete within timeout."""
        result = run_with_timeout(lambda: 42, seconds=5)
        assert result.ok is True
        assert result.timed_out is False
        assert result.result == 42

    def test_timeout_triggers(self):
        """Slow function should trigger timeout."""
        result = run_with_timeout(lambda: time.sleep(10), seconds=0.1)
        assert result.ok is False
        assert result.timed_out is True

    def test_exception_propagates(self):
        """Function that raises should return error."""
        def _fail():
            raise ValueError("test error")
        result = run_with_timeout(_fail, seconds=5)
        assert result.ok is False
        assert "test error" in result.error
