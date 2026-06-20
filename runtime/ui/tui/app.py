"""Test-Agent TUI — Textual dashboard with panel switching.

Hotkeys:
  F1 — Dashboard    F2 — Skill Browser    F3 — Agent Status
  F4 — Log Viewer    F5 — Config           F6 — Help
  F7 — Scheduler     F8 — Theme toggle    Ctrl+Q — Quit
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane
from textual.binding import Binding

from runtime.ui.tui.panels.dashboard import DashboardPanel
from runtime.ui.tui.panels.skills import SkillBrowserPanel
from runtime.ui.tui.panels.status import AgentStatusPanel
from runtime.ui.tui.panels.logs import LogViewerPanel
from runtime.ui.tui.panels.config import ConfigPanel
from runtime.ui.tui.panels.help import HelpPanel
from runtime.ui.tui.panels.scheduler_panel import SchedulerPanel
from runtime.ui.tui.panels.execution import ExecutionPanel
from runtime.ui.tui.panels.skins import SkinSelectorPanel


THEMES = {
    "dark": """
    Screen { background: #1a1a2e; }
    Header { background: #16213e; color: #e0e0e0; }
    Footer { background: #16213e; color: #888888; }
    """,
    "light": """
    Screen { background: #f5f5f5; }
    Header { background: #e0e0e0; color: #333333; }
    Footer { background: #e0e0e0; color: #666666; }
    """,
    "high-contrast": """
    Screen { background: #000000; }
    Header { background: #ffffff; color: #000000; text-style: bold; }
    Footer { background: #ffffff; color: #000000; text-style: bold; }
    """,
}


class TestAgentTUI(App):
    """Test-Agent V2.0.0 — Terminal Dashboard. Mouse + keyboard support."""

    CSS = """
    Screen {
        background: $surface;
    }
    TabbedContent {
        dock: top;
    }
    TabPane {
        padding: 1 2;
    }
    /* Responsive: compact layout for narrow terminals */
    @media (max-width: 80) {
        TabPane {
            padding: 0 1;
        }
    }
    """

    BINDINGS = [
        Binding("f1", "show_tab('dashboard')", "Dashboard", show=True),
        Binding("f2", "show_tab('skills')", "Skills", show=True),
        Binding("f3", "show_tab('status')", "Status", show=True),
        Binding("f4", "show_tab('logs')", "Logs", show=True),
        Binding("f5", "show_tab('config')", "Config", show=True),
        Binding("f6", "show_tab('execution')", "Execute", show=True),
        Binding("f7", "show_tab('scheduler')", "Scheduler", show=True),
        Binding("f8", "show_tab('help')", "Help", show=True),
        Binding("f9", "show_tab('skins')", "Skins", show=True),
        Binding("f10", "toggle_theme", "Theme", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

    _theme_index = 0
    _theme_names = list(THEMES.keys())

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="dashboard"):
            with TabPane("Dashboard", id="dashboard"):
                yield DashboardPanel()
            with TabPane("Skills", id="skills"):
                yield SkillBrowserPanel()
            with TabPane("Status", id="status"):
                yield AgentStatusPanel()
            with TabPane("Logs", id="logs"):
                yield LogViewerPanel()
            with TabPane("Config", id="config"):
                yield ConfigPanel()
            with TabPane("Execute", id="execution"):
                yield ExecutionPanel()
            with TabPane("Scheduler", id="scheduler"):
                yield SchedulerPanel()
            with TabPane("Skins", id="skins"):
                yield SkinSelectorPanel()
            with TabPane("Help", id="help"):
                yield HelpPanel()
        yield Footer()

    def action_show_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id

    def action_toggle_theme(self) -> None:
        """Cycle through 3 built-in themes: dark → light → high-contrast."""
        self._theme_index = (self._theme_index + 1) % len(self._theme_names)
        name = self._theme_names[self._theme_index]
        self.app.CSS = THEMES[name]
        self.notify(f"Theme: {name}", timeout=2)


def run_tui():
    """Entry point for `tagent tui`."""
    app = TestAgentTUI()
    app.run()
