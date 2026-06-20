"""Skill Browser panel — installed skills with categories and search."""

from textual.widgets import Static, Input, ListView, ListItem
from textual.containers import Vertical


class SkillBrowserPanel(Vertical):
    """Browse and search installed test skills with live data."""

    def compose(self):
        yield Static("Skill Browser", classes="title")
        yield Static("Type to filter skills:")
        yield Input(placeholder="Search...", id="skill-search")
        yield Static("")
        try:
            from runtime.orchestrator.skills import SKILL_RUNNERS
            skills = sorted(SKILL_RUNNERS.keys())
            yield Static(f"  {len(skills)} skills available:")
            yield Static("")
            categories = [
                ("Network", ["ping", "http"]),
                ("System", ["file", "process", "timeout"]),
                ("Pentest", ["pentest"]),
                ("Automotive", ["automotive"]),
                ("General", ["mobile", "visual", "system-test", "eval", "agent", "build"]),
            ]
            for cat, prefixes in categories:
                matches = [s for s in skills if any(s.startswith(p) for p in prefixes)]
                if matches:
                    yield Static(f"  [{cat}]")
                    for s in matches:
                        yield ListItem(Static(f"    {s}"))
            shown = set()
            for _, prefs in categories:
                for s in skills:
                    if any(s.startswith(p) for p in prefs):
                        shown.add(s)
            other = [s for s in skills if s not in shown]
            if other:
                yield Static("  [Other]")
                for s in other:
                    yield ListItem(Static(f"    {s}"))
        except Exception as e:
            yield Static(f"  Unable to load skills: {e}")
