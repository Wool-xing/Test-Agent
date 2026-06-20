<<<<<<< HEAD
"""Skill Browser panel — installed skills with counts."""
=======
"""Skill Browser panel — list/search installed skills."""
>>>>>>> 6814523518fcfd06fd81ea6a0fc72be97fd00b08

from textual.widgets import Static, ListView, ListItem
from textual.containers import Vertical


class SkillBrowserPanel(Vertical):
<<<<<<< HEAD
    """Browse installed test skills with live catalog data."""

    def compose(self):
        yield Static("Skill Browser", classes="title")
        yield Static("")
        try:
            from runtime.orchestrator.skills import SKILL_RUNNERS
            skills = sorted(SKILL_RUNNERS.keys())
            yield Static(f"  {len(skills)} skills registered:")
            yield Static("")
            for s in skills:
                yield ListItem(Static(f"    {s}"))
        except Exception as e:
            yield Static(f"  Unable to load skills: {e}")
=======
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
>>>>>>> 6814523518fcfd06fd81ea6a0fc72be97fd00b08
