"""Skill Browser panel — list/search installed skills."""

from textual.widgets import Static, ListView, ListItem
from textual.containers import Vertical


class SkillBrowserPanel(Vertical):
    """Browse and search installed test skills."""

    def compose(self):
        yield Static("Skill Browser", classes="title")
        try:
            from runtime.orchestrator.skills import SKILL_RUNNERS
            skills = sorted(SKILL_RUNNERS.keys())
            items = [ListItem(Static(f"  {s}")) for s in skills]
            yield ListView(*items)
        except Exception:
            yield Static("Unable to load skills catalog.")
