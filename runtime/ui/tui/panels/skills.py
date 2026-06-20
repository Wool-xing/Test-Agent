"""Skill Browser panel — installed skills with counts."""

from textual.widgets import Static, ListView, ListItem
from textual.containers import Vertical


class SkillBrowserPanel(Vertical):
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
