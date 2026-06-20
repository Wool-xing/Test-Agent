"""TDD tests for LLM Cost Control (§补-9)."""

from runtime.infra.cost_control import (
    TokenBudget,
    CostTracker,
    estimate_tokens,
    get_cost_tracker,
    _DOWNGRADE_CHAIN,
)


class TestTokenBudget:
    def test_default_budget(self):
        """Default budget should be 1M tokens."""
        b = TokenBudget()
        assert b.total_limit == 1_000_000
        assert b.per_task_limit == 50_000

    def test_spent_tracking(self):
        """Spending should track correctly."""
        b = TokenBudget()
        b.spent = 500_000
        assert b.remaining == 500_000
        assert b.is_exceeded is False
        b.spent = 1_000_000
        assert b.is_exceeded is True

    def test_usage_pct(self):
        """Usage percentage should be accurate."""
        b = TokenBudget(total_limit=10000)
        b.spent = 5000
        assert b.usage_pct == 50.0


class TestCostTracker:
    def test_estimate_cost(self):
        """Cost estimation should use model pricing."""
        tracker = CostTracker()
        cost = tracker.estimate_cost(1000, 1000, "claude-sonnet")
        assert cost > 0

    def test_ollama_free(self):
        """Ollama should cost zero."""
        tracker = CostTracker()
        cost = tracker.estimate_cost(1000, 1000, "ollama")
        assert cost == 0.0

    def test_record_usage(self):
        """Recording usage should update budget."""
        tracker = CostTracker(TokenBudget(total_limit=10000))
        result = tracker.record_usage(1000, 500, "claude-sonnet")
        assert result["budget_spent"] == 1500
        assert result["budget_remaining"] == 8500

    def test_suggest_downgrade(self):
        """Should suggest cheaper model."""
        tracker = CostTracker()
        assert tracker.suggest_downgrade("claude-sonnet") == "claude-haiku"
        assert tracker.suggest_downgrade("ollama") is None

    def test_should_downgrade_when_budget_low(self):
        """Should recommend downgrade when budget > 80% used."""
        tracker = CostTracker(TokenBudget(total_limit=1000, warning_threshold=0.8))
        tracker.budget.spent = 900
        assert tracker.should_downgrade("claude-sonnet") is True

    def test_should_not_downgrade_when_budget_ok(self):
        """Should not downgrade when budget is fine."""
        tracker = CostTracker(TokenBudget(total_limit=1000))
        tracker.budget.spent = 100
        assert tracker.should_downgrade("claude-sonnet") is False

    def test_singleton(self):
        """get_cost_tracker should return same instance."""
        t1 = get_cost_tracker()
        t2 = get_cost_tracker()
        assert t1 is t2


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_english_text(self):
        tokens = estimate_tokens("hello world " * 100)
        assert tokens > 0

    def test_cjk_text(self):
        tokens = estimate_tokens("你好世界" * 100)
        assert tokens > 0
