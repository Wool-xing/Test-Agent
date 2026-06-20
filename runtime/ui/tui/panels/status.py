"""Agent Status panel — live runtime configuration."""

from textual.widgets import Static
from textual.containers import Vertical


class AgentStatusPanel(Vertical):
    """Display current agent configuration with live data."""

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
            yield Static(f"  Project:      {s.project_root}")
            yield Static(f"  CI Mode:      {'yes' if s.ci_mode else 'no'}")
            yield Static(f"  Workspace:    {s.workspace_dir}")
        except Exception as e:
            yield Static(f"  Configuration unavailable: {e}")
