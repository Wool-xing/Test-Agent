"""Interactive REPL UI — rendering helpers extracted from interactive.py.

These functions handle banner, help, key bindings, Rich→prompt_toolkit conversion,
and diagnostic error messages. They are imported back into interactive.py.
"""

from __future__ import annotations

import os
import re
import sys
from typing import Any

from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.text import Text as RichText

from runtime.cli._shared import console


# ── Key bindings ─────────────────────────────────────────────────────


def make_keybindings() -> KeyBindings:
    """Create standard REPL key bindings."""
    kb = KeyBindings()

    @kb.add("enter")
    def _insert_newline(event: Any) -> None:
        buffer = event.current_buffer
        text = buffer.text
        if text.endswith("\\"):
            buffer.insert_text("\n")
        else:
            buffer.validate_and_handle()

    @kb.add("c-d")
    def _ctrl_d_exit(event: Any) -> None:
        text = event.current_buffer.text
        if text == "" or text.isspace():
            event.app.exit()
        else:
            buffer = event.current_buffer
            if buffer.cursor_position < len(buffer.text):
                buffer.delete()

    @kb.add("c-s")
    def _redraw_screen(event: Any) -> None:
        event.app.renderer.clear()
        event.app._request_absolute_cursor_position()

    return kb


# ── Multiline input helpers ──────────────────────────────────────────


def is_multiline_candidate(text: str) -> bool:
    """Check if text likely needs multiline input."""
    return len(text) > 120 or "\n" in text or "```" in text


# ── Emoji icon helper ────────────────────────────────────────────────


def _icon(kind: str) -> str:
    """Return emoji for common health/status categories."""
    icons: dict[str, str] = {
        "ok": "✅", "error": "❌", "warn": "⚠️", "info": "ℹ️",
        "pending": "⏳", "running": "🔄", "done": "✅", "fail": "❌",
        "skip": "⏭️", "timeout": "⏰", "cancelled": "🚫",
    }
    return icons.get(kind, "•")


# ── Terminal utilities ───────────────────────────────────────────────


def _term_width() -> int:
    """Return terminal width, default 80."""
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 80


def _git_branch() -> str:
    """Return current git branch name, or '?'."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=2,
        )
        return result.stdout.strip() or "?"
    except Exception:
        return "?"


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def _context_pct(memory: Any) -> int:
    """Estimate context window usage percentage."""
    try:
        tokens = sum(_estimate_tokens(m.content or "") for m in memory.messages)
        return min(99, int(tokens / 200000 * 100))
    except Exception:
        return 0


def _fit_line(width: int, parts: list[str]) -> str:
    """Fit as many parts as possible into `width` columns.
    Joins with " · ". Drops rightmost first."""
    sep = " · "
    full = sep.join(parts)
    if len(re.sub(r'<[^>]+>', '', full)) <= width:
        return full
    for n in range(len(parts) - 1, 0, -1):
        candidate = sep.join(parts[:n])
        if len(re.sub(r'<[^>]+>', '', candidate)) <= width:
            return candidate
    return parts[0]


def _set_terminal_title(proj: str, model: str) -> None:
    """Set terminal title via OSC escape."""
    try:
        sys.stdout.write(f"\033]0;Test-Agent: {proj} ({model})\007")
        sys.stdout.flush()
    except Exception:
        pass


# ── Banner & Help ─────────────────────────────────────────────────────


_SHEEP = r"""
    ✧  ▗▛ 🐏 ▜▖  ✧
         ▀▀▀▀▀
         ▐▌ ▐▌

  ૮₍˶ᵔ ᗜ ᵔ˶₎ა  Test-Agent v{version}
  AI Router · {experts} Experts · {skills} Skills"""


def print_banner(
    current_provider: str,
    current_model: str,
    project_root: str,
    cached_health: list[dict],
) -> None:
    """Compact banner: sheep + version + model + project."""
    try:
        from runtime.cli.skins import apply_skin_to_banner
        banner = apply_skin_to_banner()
    except Exception:
        banner = _SHEEP
    console.print(banner)
    console.print(f"  [bold cyan]{current_provider}[/] · [dim]{current_model}[/]")
    console.print(f"  [dim]{project_root}[/]")

    errors = [i for i in cached_health if i["level"] == "error"]
    warnings = [i for i in cached_health if i["level"] == "warning"]
    ico = _icon("warn")
    if errors:
        console.print(f"  [red]{ico} {len(errors)} errors[/] · [dim]!doctor[/]")
    elif warnings:
        console.print(f"  [yellow]{ico} {len(warnings)} warnings[/] · [dim]!doctor[/]")
    console.print()


def print_banner_transcript(
    tui: Any,
    current_provider: str,
    current_model: str,
    project_root: str,
    cached_health: list[dict],
    memory: Any,
) -> None:
    """Seed transcript TUI with banner + provider/model/project + health + stats."""
    try:
        from runtime.cli.skins import apply_skin_to_banner
        banner = apply_skin_to_banner()
    except Exception:
        banner = _SHEEP
    tui.append_output(banner)
    tui.append_output(f"  [bold cyan]{current_provider}[/] · [dim]{current_model}[/]")
    tui.append_output(f"  [dim]{project_root}[/]")

    errors = [i for i in cached_health if i["level"] == "error"]
    warnings = [i for i in cached_health if i["level"] == "warning"]
    if errors:
        tui.append_output(f"  [red]⚠ {len(errors)} errors[/] · [dim]!doctor[/]")
    elif warnings:
        tui.append_output(f"  [yellow]⚠ {len(warnings)} warnings[/] · [dim]!doctor[/]")

    parts: list[str] = []
    try:
        from runtime.cli.conversation import _discover_project_context, load_memory_md
        if _discover_project_context():
            parts.append("[dim]📋 CLAUDE.md[/]")
    except Exception:
        pass
    try:
        md = load_memory_md()
        if md:
            parts.append(f"[dim]🧠 {md.count(chr(10)) + 1}f[/]")
    except Exception:
        pass
    if memory.messages:
        parts.append(f"[dim]{len(memory.messages)} turns[/]")
    if parts:
        tui.append_output("  " + " · ".join(parts))


def print_help() -> None:
    """Print full command reference, grouped by category."""
    from rich.panel import Panel

    groups = [
        ("Run", [
            ("!task add|list|done|start", "Manage task list with criteria"),
            ("!test  <target>", "Full 11-step test pipeline"),
            ("!run   <target>", "Plan + execute (quick)"),
            ("!plan  <target>", "Plan only, no execution"),
        ]),
        ("Data & API", [
            ("!data users|related <N>", "Generate test data"),
            ("!api gen|test", "OpenAPI contract testing"),
            ("!cross env <e1> <e2>", "Cross-environment test run"),
        ]),
        ("Quality", [
            ("!regression", "Regression detection vs baseline"),
            ("!flaky list|quarantine", "Flaky test management"),
            ("!prioritize", "Prioritize by git changes"),
            ("!clean", "Clean temp data (preserves deliverables)"),
        ]),
        ("Info", [
            ("!update", "Check for newer version"),
            ("!progress", "Test coverage matrix"),
            ("!status", "Session, model, conversation stats"),
            ("!tools", "List agents + skills with status"),
            ("!ls", "Quick list experts + skills"),
            ("!doctor [--agents]", "Environment health check"),
            ("!ready", "Release readiness score"),
        ]),
        ("Control", [
            ("!model [provider] [model]", "Switch LLM (Tab to complete)"),
            ("!lang [zh|en|zh-en]", "Switch UI language"),
            ("!skin [name]", "Switch CLI theme (4 skins)"),
            ("!fc", "Fix last typo (like thefuck)"),
            ("!1..9", "Command history / re-run"),
            ("!alias add|list", "Command shortcuts"),
            ("!personality [name]", "Set agent persona (loads expert)"),
            ("!clear", "Reset conversation memory"),
            ("!undo", "Remove last exchange from memory"),
            ("!retry", "Re-run last prompt after undo"),
            ("!setup [--preset]", "Generate config files"),
            ("!check [--e2e]", "Framework self-test"),
        ]),
        ("Automation", [
            ("!hook add|list|prebuilt", "Lifecycle hooks (before/after/error)"),
        ]),
        ("Learning", [
            ("!distill", "Save last execution as reusable skill"),
        ]),
        ("Memory", [
            ("!remember <fact>", "Save fact to MEMORY.md"),
            ("!forget <keyword>", "Remove facts by keyword"),
            ("!nudge", "Scan session for facts worth remembering"),
            ("!memory", "Show MEMORY.md contents"),
        ]),
        ("Workspace", [
            ("!ws add|list|switch|auto", "Manage project workspaces"),
        ]),
        ("Gateway", [
            ("!gateway", "IM platform connection status"),
        ]),
        ("Session", [
            ("!cost", "Token usage and cost estimate"),
            ("!cache [clear]", "LLM response cache stats/clear"),
            ("!insights [days]", "Cross-session usage analytics"),
            ("!sessions", "List saved sessions"),
            ("!resume <id>", "Load a saved session"),
            ("!save", "Export conversation to markdown"),
            ("!compact", "Summarize and compress context"),
            ("!context", "Full conversation history"),
            ("!help", "This help"),
            ("!quit  (Ctrl+D)", "Save session and exit"),
        ]),
    ]

    console.print()
    for title, items in groups:
        body = "\n".join(f"  {cmd:22s} {desc}" for cmd, desc in items)
        console.print(Panel(body, title=title, title_align="left"))
    console.print("[dim]↑↓ history · Tab completion · Bare text → LLM routing[/]")
    console.print()


# ── Error Diagnosis ───────────────────────────────────────────────────


def diagnose_error(exc: Exception, current_provider: str) -> str | None:
    """Return a friendly Chinese/English hint for common errors. None if no specific advice."""
    _msg = str(exc).lower()
    _t = type(exc).__name__

    # API key / auth errors
    if any(k in _msg for k in ("api_key", "api key", "apikey", "unauthorized", "401", "credential", "authentication")):
        return (
            f"LLM ({current_provider}) needs an API key. "
            f"Set [cyan]TAGENT_LLM_API_KEY[/] in [cyan].env[/] or environment. "
            f"Run [cyan]tagent setup --preset minimal[/] to generate a template."
        )

    # Missing module / import errors
    if _t in ("ModuleNotFoundError", "ImportError"):
        mod = _msg.split("'")[1] if "'" in _msg else "?"
        return (
            f"Missing Python package: [cyan]{mod}[/]. "
            f"Run [cyan]pip install -e runtime/[/] or [cyan]pip install {mod}[/]."
        )

    # Connection / network errors
    if any(k in _msg for k in ("connection", "timeout", "refused", "unreachable", "ssl", "dns", "resolve")):
        return (
            f"Cannot reach the LLM service. Check your network, proxy settings, "
            f"or [cyan]TAGENT_LLM_API_BASE[/] in [cyan].env[/]."
        )

    return None


# ── Rich → prompt_toolkit conversion ──────────────────────────────────


def rich_to_pt(markup: str) -> FormattedText:
    """Convert Rich markup string to prompt_toolkit FormattedText."""
    rt = RichText.from_markup(markup)
    segments: list[tuple[str, str]] = []
    for span in rt.spans:
        start = span.start
        end = span.end
        text = rt.plain[start:end]
        style_str = str(span.style) if span.style else ""
        pt_style = _rich_style_to_pt(style_str)
        segments.append((pt_style, text))
    return FormattedText(segments)


def _rich_style_to_pt(rich_style: str) -> str:
    """Map a Rich style string to a prompt_toolkit style string."""
    mapping: dict[str, str] = {
        "bold": "bold", "dim": "ansigray", "italic": "italic",
        "cyan": "ansicyan", "bright_cyan": "ansicyan",
        "green": "ansigreen", "bright_green": "ansigreen",
        "red": "ansired", "bright_red": "ansired",
        "yellow": "ansiyellow", "bright_yellow": "ansiyellow",
        "blue": "ansiblue", "magenta": "ansimagenta",
        "white": "", "bright_white": "bold",
        "black": "ansigray", "default": "",
    }
    parts = []
    for token in rich_style.split():
        token = token.strip()
        if not token:
            continue
        mapped = mapping.get(token, "")
        if mapped:
            parts.append(mapped)
    return " ".join(parts)


def repl_print(markup: str = "", **kwargs: object) -> None:
    """Print to TUI via prompt_toolkit — does NOT corrupt terminal layout."""
    from prompt_toolkit import print_formatted_text as pt_print
    try:
        ft = rich_to_pt(markup)
        pt_print(ft)
    except Exception:
        plain = re.sub(r'\[[^\]]*\]', '', markup)
        pt_print(FormattedText([("", plain)]))


# ── Prompt style ──────────────────────────────────────────────────────


def get_prompt_style() -> Style:
    """Build prompt_toolkit Style from active skin's colors (dynamic, not hardcoded)."""
    try:
        from runtime.cli.colorscheme import get_colorscheme
        return get_colorscheme().pt_style()
    except Exception:
        return Style.from_dict({})
