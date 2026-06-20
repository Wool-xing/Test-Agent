"""Skin Selector panel — preview and switch themes."""

from textual.widgets import Static, ListView, ListItem
from textual.containers import Vertical


THEME_LIST = [
    ("dark", "#1a1a2e background, green/cyan accents"),
    ("light", "#f5f5f5 background, muted colors"),
    ("high-contrast", "#000000 background, white bold text, maximum readability"),
]


class SkinSelectorPanel(Vertical):
    """Preview and switch built-in themes."""

    def compose(self):
        yield Static("Theme / Skin Selector", classes="title")
        yield Static("")
        yield Static("  Built-in Themes (F8 to cycle):")
        yield Static("")
        for name, desc in THEME_LIST:
            yield Static(f"  [bold]{name}[/] — {desc}")
        yield Static("")
        yield Static("  Custom themes: add CSS to ~/.tagent/themes/")
        yield Static("  See docs/getting-started/themes.md")
