"""Test-Agent TUI — Textual dashboard with panel switching.

Hotkeys:
  F1 — Dashboard    F2 — Skill Browser    F3 — Agent Status
  F4 — Log Viewer    F5 — Config    F6 — Help
  Ctrl+Q — Quit
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, TabbedContent, TabPane
from textual.binding import Binding

from runtime.ui.tui.panels.dashboard import DashboardPanel
from runtime.ui.tui.panels.skills import SkillBrowserPanel
from runtime.ui.tui.panels.status import AgentStatusPanel
from runtime.ui.tui.panels.logs import LogViewerPanel
from runtime.ui.tui.panels.config import ConfigPanel
from runtime.ui.tui.panels.help import HelpPanel


class TestAgentTUI(App):
    """Test-Agent V2.0.0 — Terminal Dashboard."""

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
    """

    BINDINGS = [
        Binding("f1", "show_tab('dashboard')", "Dashboard", show=True),
        Binding("f2", "show_tab('skills')", "Skills", show=True),
        Binding("f3", "show_tab('status')", "Status", show=True),
        Binding("f4", "show_tab('logs')", "Logs", show=True),
        Binding("f5", "show_tab('config')", "Config", show=True),
        Binding("f6", "show_tab('help')", "Help", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
    ]

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
            with TabPane("Help", id="help"):
                yield HelpPanel()
        yield Footer()

    def action_show_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id


def run_tui():
    """Entry point for `tagent tui`."""
    app = TestAgentTUI()
    app.run()
