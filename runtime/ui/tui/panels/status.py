"""Agent Status panel — LLM provider, model, token usage, session info."""

from textual.widgets import Static
from textual.containers import Vertical


class AgentStatusPanel(Vertical):
    """Display current agent configuration and runtime status."""

    def compose(self):
        yield Static("Agent Status", classes="title")
        try:
            from runtime.config.settings import get_settings
            s = get_settings()
            lines = [
                f"Provider: {s.llm_provider}",
                f"Model: (see TAGENT_LLM_MODEL env)",
                f"Max workers: {s.max_concurrent_runs}",
                f"Timeout: {s.test_timeout_seconds}s",
            ]
            for line in lines:
                yield Static(f"  {line}")
        except Exception:
            yield Static("Unable to load agent status.")
