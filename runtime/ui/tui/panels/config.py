<<<<<<< HEAD
"""Config panel — key settings overview."""
=======
"""Config Editor panel — view and edit configuration."""
>>>>>>> 6814523518fcfd06fd81ea6a0fc72be97fd00b08

from textual.widgets import Static
from textual.containers import Vertical


class ConfigPanel(Vertical):
<<<<<<< HEAD
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
=======
    """View and manage Test-Agent configuration."""

    def compose(self):
        yield Static("Configuration", classes="title")
        try:
            from runtime.config.settings import get_settings
            s = get_settings()
            cfg_items = [
                f"llm_provider: {s.llm_provider}",
                f"project_root: {s.project_root}",
                f"workspace_dir: {s.workspace_dir}",
                f"api_host: {s.api_host}:{s.api_port}",
                f"ci_mode: {s.ci_mode}",
            ]
            for item in cfg_items:
                yield Static(f"  {item}")
        except Exception:
            yield Static("Unable to load configuration.")
>>>>>>> 6814523518fcfd06fd81ea6a0fc72be97fd00b08
