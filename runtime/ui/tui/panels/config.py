"""Config Editor panel — view and edit configuration."""

from textual.widgets import Static
from textual.containers import Vertical


class ConfigPanel(Vertical):
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
