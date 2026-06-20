"""Agent Status panel — live runtime + token usage tracking."""

from textual.widgets import Static
from textual.containers import Vertical


class AgentStatusPanel(Vertical):
    """Display agent configuration + token/cost tracking."""

    def compose(self):
        yield Static("Agent Status", classes="title")
        yield Static("")
        try:
            from runtime.config.settings import get_settings
            import os
            s = get_settings()
            model = os.environ.get("TAGENT_LLM_MODEL", "default")
            yield Static(f"  Provider:     {s.llm_provider}")
            yield Static(f"  Model:        {model}")
            yield Static(f"  Max Workers:  {s.max_concurrent_runs}")
            yield Static(f"  Timeout:      {s.test_timeout_seconds}s")
            yield Static(f"  CI Mode:      {'yes' if s.ci_mode else 'no'}")
        except Exception as e:
            yield Static(f"  Config error: {e}")
        yield Static("")
        yield Static("Token Usage:")
        try:
            from runtime.infra.cost_control import get_cost_tracker
            tracker = get_cost_tracker()
            budget = tracker.budget
            yield Static(f"  Spent:    {budget.spent:,} tokens")
            yield Static(f"  Remaining: {budget.remaining:,} tokens")
            yield Static(f"  Usage:    {budget.usage_pct:.1f}%")
            cost = tracker.estimate_cost(budget.spent, 0, "claude-sonnet")
            yield Static(f"  Est Cost: ${cost:.4f}")
        except Exception:
            yield Static("  Token tracking: unavailable")
        yield Static("")
        yield Static("Session:")
        try:
            from pathlib import Path
            import json, time
            sf = Path("workspace/gateway/active_session.json")
            if sf.exists():
                data = json.loads(sf.read_text(encoding="utf-8"))
                started = data.get("started_at", 0)
                if isinstance(started, (int, float)) and started > 0:
                    elapsed = int(time.time() - started)
                    m, s = divmod(elapsed, 60)
                    h, m = divmod(m, 60)
                    yield Static(f"  Uptime: {h}h {m}m {s}s")
                    yield Static(f"  Branch: {data.get('branch', 'unknown')}")
        except Exception:
            yield Static("  Session info: unavailable")
