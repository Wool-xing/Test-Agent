"""LLM Cost Control (§补-9) — Token budget, cost estimation, model downgrade.

Features:
- Project-level token budget (tagent config set budget.token_limit)
- Per-task budget (tagent run --budget)
- Cost estimation before execution
- Real-time token tracking
- Model downgrade: Opus→Sonnet→Haiku→Ollama when budget low
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class TokenBudget:
    """Token budget configuration."""
    total_limit: int = 1_000_000       # Project-level
    per_task_limit: int = 50_000        # Per-task default
    warning_threshold: float = 0.8      # Warn at 80%
    spent: int = 0
    task_spent: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.total_limit - self.spent)

    @property
    def task_remaining(self) -> int:
        return max(0, self.per_task_limit - self.task_spent)

    @property
    def is_exceeded(self) -> bool:
        return self.spent >= self.total_limit

    @property
    def is_task_exceeded(self) -> bool:
        return self.task_spent >= self.per_task_limit

    @property
    def usage_pct(self) -> float:
        return self.spent / self.total_limit * 100 if self.total_limit > 0 else 0


# Model pricing ($/1K tokens)
_MODEL_PRICES: dict[str, tuple[float, float]] = {
    "claude-opus": (0.015, 0.075),
    "claude-sonnet": (0.003, 0.015),
    "claude-haiku": (0.0008, 0.004),
    "gpt-4o": (0.0025, 0.01),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gemini-pro": (0.000125, 0.000375),
    "gemini-flash": (0.000075, 0.0003),
    "deepseek-chat": (0.00027, 0.0011),
    "qwen-plus": (0.0005, 0.002),
    "ollama": (0, 0),
}

# Model downgrade chain
_DOWNGRADE_CHAIN: dict[str, str] = {
    "claude-opus": "claude-sonnet",
    "claude-sonnet": "claude-haiku",
    "claude-haiku": "ollama",
    "gpt-4o": "gpt-4o-mini",
    "gpt-4o-mini": "ollama",
    "gemini-pro": "gemini-flash",
    "gemini-flash": "ollama",
    "deepseek-chat": "ollama",
    "qwen-plus": "ollama",
}


class CostTracker:
    """Track token usage and costs."""

    def __init__(self, budget: TokenBudget | None = None):
        self.budget = budget or TokenBudget()
        self._lock = threading.Lock()
        self._callbacks: list[Callable] = []

    def estimate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Estimate cost for token counts."""
        in_price, out_price = _MODEL_PRICES.get(model, (0, 0))
        return (input_tokens / 1000) * in_price + (output_tokens / 1000) * out_price

    def record_usage(self, input_tokens: int, output_tokens: int, model: str) -> dict:
        """Record token usage and check budget."""
        with self._lock:
            self.budget.spent += input_tokens + output_tokens
            self.budget.task_spent += input_tokens + output_tokens
            cost = self.estimate_cost(input_tokens, output_tokens, model)
            exceeded = self.budget.is_exceeded or self.budget.is_task_exceeded
            result = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "budget_spent": self.budget.spent,
                "budget_remaining": self.budget.remaining,
                "task_spent": self.budget.task_spent,
                "task_remaining": self.budget.task_remaining,
                "budget_exceeded": exceeded,
            }
            if exceeded:
                for cb in self._callbacks:
                    cb(result)
            return result

    def reset_task(self) -> None:
        """Reset per-task counter."""
        with self._lock:
            self.budget.task_spent = 0

    def on_budget_exceeded(self, callback: Callable) -> None:
        """Register callback for budget exceeded events."""
        self._callbacks.append(callback)

    def suggest_downgrade(self, model: str) -> str | None:
        """Suggest a cheaper model if available."""
        return _DOWNGRADE_CHAIN.get(model)

    def should_downgrade(self, model: str) -> bool:
        """Check if model should be downgraded based on budget."""
        if self.budget.usage_pct > self.budget.warning_threshold * 100:
            return self.suggest_downgrade(model) is not None
        return False


def estimate_tokens(text: str) -> int:
    """Heuristic token estimation: ~4 chars per token for English, ~2 for CJK."""
    if not text:
        return 0
    cjk = sum(1 for c in text if '一' <= c <= '鿿' or '぀' <= c <= 'ヿ')
    ascii_chars = len(text) - cjk
    return max(1, (ascii_chars // 4) + (cjk * 2 // 3))


# Singleton
_tracker: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker
