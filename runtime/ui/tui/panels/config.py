"""Config panel — key settings overview."""

from textual.widgets import Static
from textual.containers import Vertical


class ConfigPanel(Vertical):
    """View key configuration (no secrets exposed)."""

    def compose(self):
        yield Static("Configuration", classes="title")
        yield Static("")
        try:
            from runtime.config.settings import get_settings
            import os
            s = get_settings()
            yield Static(f"  Project Root:  {s.project_root}")
            yield Static(f"  Workspace:     {s.workspace_dir}")
            yield Static(f"  DB:            {s.db_url.split('://')[0] if '://' in s.db_url else 'sqlite'}")
            yield Static(f"  Max Workers:   {s.max_concurrent_runs}")
            yield Static(f"  LLM Timeout:   {s.llm_timeout_seconds}s")
            yield Static(f"  Agent Tokens:  {s.agent_max_tokens}")
            yield Static("")
            yield Static("  Sensitive values (keys, tokens) hidden.")
        except Exception as e:
            yield Static(f"  Configuration unavailable: {e}")
