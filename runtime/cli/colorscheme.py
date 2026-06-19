"""Unified color bridge: skin definitions → Rich Console + prompt_toolkit Style + HTML.

Single source of truth. Reads from active skin (skins.py) and provides
style tokens for all three rendering systems used by the TUI.

DeepSeek/OI pattern: dim() mapped to explicit palette color, not OS-dependent.
"""

from __future__ import annotations

from dataclasses import dataclass

from prompt_toolkit.styles import Style as PtStyle

# ── prompt_toolkit style name ← skin color name ──
_SKIN_TO_PT = {
    "primary": "cyan",
    "success": "green",
    "error":   "red",
    "warning": "yellow",
    "dim":     "ansigray",
}


@dataclass(frozen=True)
class ColorScheme:
    """Immutable color bridge built from a skin dict."""

    skin: dict  # from skins.get_skin()

    # ── prompt_toolkit Style ──

    def pt_style(self) -> PtStyle:
        """Build prompt_toolkit Style object for PromptSession."""
        c = self.skin.get("colors", {})
        primary = _SKIN_TO_PT.get(c.get("primary", ""), "cyan")
        dim_pt = _SKIN_TO_PT.get(c.get("dim", ""), "ansigray")

        return PtStyle.from_dict({
            "prompt": f"bold {primary}",
            "prompt.dim": dim_pt,
            "separator": self._hex_for(dim_pt),
            "bottom-toolbar": "bg:#1a1a2e fg:#a0a0c0",
            "bottom-toolbar.separator": "#444444",
        })

    @staticmethod
    def _hex_for(name: str) -> str:
        _m = {"ansigray": "#888888", "cyan": "#00aaaa", "green": "#00aa00",
              "red": "#aa0000", "yellow": "#aaaa00", "ansired": "#aa0000",
              "ansigreen": "#00aa00", "ansiyellow": "#aaaa00"}
        return _m.get(name, "#888888")

    # ── prompt_toolkit HTML ──

    def pt_html_tag(self, kind: str) -> str:
        """Get prompt_toolkit compatible HTML open tag. e.g. kind='error' → '<ansired>'"""
        c = self.skin.get("colors", {}).get(kind, "")
        mapping = {"primary": "ansicyan", "success": "ansigreen",
                   "error": "ansired", "warning": "ansiyellow",
                   "dim": "ansigray"}
        return f"<{mapping.get(c, mapping.get(kind, 'ansigray'))}>"

    def pt_html_close(self, kind: str) -> str:
        tag = self.pt_html_tag(kind)
        return tag.replace("<", "</")

    def wrap_html(self, kind: str, text: str) -> str:
        """Wrap text in prompt_toolkit HTML tags. e.g. wrap('primary', 'hello') → '<ansicyan>hello</ansicyan>'"""
        return f"{self.pt_html_tag(kind)}{text}{self.pt_html_close(kind)}"

    # ── Icons ──

    def icon(self, kind: str) -> str:
        """Get icon for kind from active skin. Falls back to defaults."""
        icons = self.skin.get("icons", {})
        defaults = {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"}
        return icons.get(kind, defaults.get(kind, ""))


# ── Singleton access ──

_scheme: ColorScheme | None = None


def get_colorscheme() -> ColorScheme:
    """Get or build ColorScheme from active skin. Cached until skin changes."""
    global _scheme
    if _scheme is None:
        from runtime.cli.skins import get_skin
        _scheme = ColorScheme(skin=get_skin())
    return _scheme


def rebuild_colorscheme() -> ColorScheme:
    """Force rebuild after skin change (e.g. !skin command)."""
    global _scheme
    from runtime.cli.skins import get_skin
    _scheme = ColorScheme(skin=get_skin())
    return _scheme
