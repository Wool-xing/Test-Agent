"""CLI skin/theming system.

Each skin defines: banner, colors, icons, prompt style.
Switch with /skin <name>, persists via user profile.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

# Built-in skins
SKINS: dict[str, dict[str, Any]] = {
    "default": {
        "name": "default",
        "description": "Original Test-Agent sheep mascot",
        "banner": r"""
    ✧  ▗▛ 🐏 ▜▖  ✧
         ▀▀▀▀▀
         ▐▌ ▐▌

  ૮₍˶ᵔ ᗜ ᵔ˶₎ა  Test-Agent v{version}
  AI Router · {experts} Experts · {skills} Skills
  Type /help for commands, or describe your test task.""",
        "prompt_style": {
            "prompt": "bold cyan",
            "prompt.dim": "dim",
        },
        "colors": {
            "primary": "cyan",
            "success": "green",
            "error": "red",
            "warning": "yellow",
            "dim": "dim",
        },
        "icons": {
            "ok": "✓",
            "fail": "✗",
            "warn": "⚠",
            "info": "💡",
        },
    },
    "dark": {
        "name": "dark",
        "description": "High-contrast dark terminal theme",
        "banner": r"""
    ╔══════════════════════╗
    ║  🧪 Test-Agent {version}  ║
    ╚══════════════════════╝

    {experts} Experts · {skills} Skills · /help for commands""",
        "prompt_style": {
            "prompt": "bold bright_cyan",
            "prompt.dim": "bright_black",
        },
        "colors": {
            "primary": "bright_cyan",
            "success": "bright_green",
            "error": "bright_red",
            "warning": "bright_yellow",
            "dim": "bright_black",
        },
        "icons": {
            "ok": "[✓]",
            "fail": "[✗]",
            "warn": "[!]",
            "info": "[i]",
        },
    },
    "minimal": {
        "name": "minimal",
        "description": "Clean, no-emoji, log-friendly output",
        "banner": "Test-Agent v{version}  |  {experts} experts  |  {skills} skills  |  /help",
        "prompt_style": {
            "prompt": "",
            "prompt.dim": "dim",
        },
        "colors": {
            "primary": "",
            "success": "",
            "error": "",
            "warning": "",
            "dim": "dim",
        },
        "icons": {
            "ok": "OK",
            "fail": "FAIL",
            "warn": "WARN",
            "info": "TIP",
        },
    },
    "retro": {
        "name": "retro",
        "description": "Monospace terminal aesthetic, 1990s style",
        "banner": r"""
+----------------------------------+
|  TEST-AGENT v{version}           |
|  {experts} agents · {skills} skills      |
+----------------------------------+
  READY.  Type /help for commands.""",
        "prompt_style": {
            "prompt": "bold green",
            "prompt.dim": "dim",
        },
        "colors": {
            "primary": "green",
            "success": "green",
            "error": "red",
            "warning": "yellow",
            "dim": "dim",
        },
        "icons": {
            "ok": "OK",
            "fail": "ERR",
            "warn": "WRN",
            "info": ">>>",
        },
    },
    "matrix": {
        "name": "matrix",
        "description": "Hacker green-on-black, pentest/security vibe",
        "banner": r"""
    ╔══════════════════════════════════════╗
    ║  >> TEST-AGENT_v{version}           ║
    ║  >> {experts}_agents :: {skills}_skills         ║
    ║  >> trace active :: /help           ║
    ╚══════════════════════════════════════╝
      >>>>  follow the white rabbit.  >>>>""",
        "prompt_style": {
            "prompt": "bold green",
            "prompt.dim": "dim green",
        },
        "colors": {
            "primary": "green",
            "success": "bright_green",
            "error": "red",
            "warning": "yellow",
            "dim": "dim green",
        },
        "icons": {
            "ok": "OK",
            "fail": "ERR",
            "warn": "WARN",
            "info": ">>>",
        },
    },
    "dracula": {
        "name": "dracula",
        "description": "Popular dark theme with purple accents",
        "banner": r"""
    █ █▄ █ · Test-Agent v{version}
    █ █ ▀█ · {experts} agents / {skills} skills
    ▀ ▀  ▀ · /help for commands""",
        "prompt_style": {
            "prompt": "bold magenta",
            "prompt.dim": "dim",
        },
        "colors": {
            "primary": "magenta",
            "success": "bright_green",
            "error": "bright_red",
            "warning": "bright_yellow",
            "dim": "bright_black",
        },
        "icons": {
            "ok": "✓",
            "fail": "✗",
            "warn": "⚠",
            "info": "💡",
        },
    },
    "monokai": {
        "name": "monokai",
        "description": "Code editor theme — warm syntax colors",
        "banner": r"""
  ███╗   ███╗ Test-Agent v{version}
  ████╗ ████║ {experts} experts · {skills} skills
  ██╔████╔██║ /help for commands
  ██║╚██╔╝██║
  ╚═╝ ╚═╝ ╚═╝""",
        "prompt_style": {
            "prompt": "bold yellow",
            "prompt.dim": "dim",
        },
        "colors": {
            "primary": "yellow",
            "success": "bright_green",
            "error": "bright_red",
            "warning": "yellow",
            "dim": "bright_black",
        },
        "icons": {
            "ok": "✓",
            "fail": "✗",
            "warn": "⚠",
            "info": "💡",
        },
    },
    "nord": {
        "name": "nord",
        "description": "Arctic bluish-gray, calm and focused",
        "banner": r"""
        ╭─────────────────────────╮
        │  Test-Agent v{version}      │
        │  {experts} experts · {skills} skills  │
        │  /help for commands     │
        ╰─────────────────────────╯""",
        "prompt_style": {
            "prompt": "bold bright_cyan",
            "prompt.dim": "dim",
        },
        "colors": {
            "primary": "bright_cyan",
            "success": "bright_green",
            "error": "bright_red",
            "warning": "bright_yellow",
            "dim": "bright_black",
        },
        "icons": {
            "ok": "✓",
            "fail": "✗",
            "warn": "⚠",
            "info": "💡",
        },
    },
    "terminal": {
        "name": "terminal",
        "description": "Classic green phosphor terminal, testing engineer standard",
        "banner": r"""
$ test-agent --version
Test-Agent v{version} | {experts} agents | {skills} skills
$ echo 'Type /help for commands'
Type /help for commands
$ _""",
        "prompt_style": {
            "prompt": "bold bright_green",
            "prompt.dim": "dim green",
        },
        "colors": {
            "primary": "bright_green",
            "success": "green",
            "error": "red",
            "warning": "yellow",
            "dim": "dim green",
        },
        "icons": {
            "ok": "[  OK  ]",
            "fail": "[ FAIL ]",
            "warn": "[ WARN ]",
            "info": "[ INFO ]",
        },
    },
}


def get_skin(name: str | None = None) -> dict[str, Any]:
    """Get a skin by name. Returns default if not found."""
    if name is None:
        name = os.environ.get("TAGENT_SKIN", "default")
    return SKINS.get(name, SKINS["default"])


def get_current_skin_name() -> str:
    return os.environ.get("TAGENT_SKIN", "default")


def set_skin(name: str) -> bool:
    """Set active skin. Returns True if skin exists."""
    if name not in SKINS:
        return False
    os.environ["TAGENT_SKIN"] = name
    return True


def list_skins() -> list[dict[str, str]]:
    """List all available skins."""
    current = get_current_skin_name()
    return [
        {"name": s["name"], "description": s["description"],
         "active": s["name"] == current}
        for s in SKINS.values()
    ]


def apply_skin_to_banner(skin_name: str | None = None) -> str:
    """Get the formatted banner for the current skin."""
    import runtime
    from runtime.cli.interactive import _count_md_files
    skin = get_skin(skin_name)
    return skin["banner"].format(
        version=runtime.__version__,
        experts=_count_md_files("agents"),
        skills=_count_md_files("skills"),
    )
