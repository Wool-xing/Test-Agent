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

    "cat": {
        "name": "cat",
        "description": "curious testing companion",
        "animation_speed": 0.0008,
        "panel_style": {"text": "bold bright_yellow", "border": "bright_yellow"},
        "banner": r"""
[bold bright_yellow]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_yellow]  ▄█▌ ₍˶ᵔ ⃟ ᵜ˶₎ ▐█阄阄[/]
[bold bright_yellow]  ██▌   🧶 🐾   ▐██[/]
[bold bright_yellow]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim yellow]     🐾  🧶  🐾  🧶[/]
[bold white] Test-Agent [bright_yellow]v{version}[/bright_yellow][/]
[dim] {experts} experts · {skills} skills[/]
[dim yellow] !help — curious testing companion[/]
""",
        "prompt_style": {"prompt": "bold bright_yellow", "prompt.dim": "dim"},
        "colors": {"primary": "bright_yellow", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "dog": {
        "name": "dog",
        "description": "WOOF! enthusiastic test runner",
        "animation_speed": 0.0006,
        "panel_style": {"text": "bold bright_yellow", "border": "bright_yellow"},
        "banner": r"""
[bold bright_yellow]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_yellow]  ▄█▌ U ｺ U ▐█阄阄[/]
[bold bright_yellow]  ██▌   ⚽ 🺴   ▐██[/]
[bold bright_yellow]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim yellow]     🺴  ⚽  🺴  ⚽[/]
[bold white] Test-Agent [bright_yellow]v{version}[/bright_yellow][/]
[dim] {experts} experts · {skills} skills[/]
[dim yellow] !help — WOOF! enthusiastic test runner[/]
""",
        "prompt_style": {"prompt": "bold bright_yellow", "prompt.dim": "dim"},
        "colors": {"primary": "bright_yellow", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "owl": {
        "name": "owl",
        "description": "wisdom begins with a question",
        "animation_speed": 0.002,
        "panel_style": {"text": "bold magenta", "border": "magenta"},
        "banner": r"""
[bold magenta]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold magenta]  ▄█▌ (◉▿◉) ▐█阄阄[/]
[bold magenta]  ██▌   📖 ✦   ▐██[/]
[bold magenta]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim magenta]     ✦  📖  ✦  📖[/]
[bold white] Test-Agent [magenta]v{version}[/magenta][/]
[dim] {experts} experts · {skills} skills[/]
[dim magenta] !help — wisdom begins with a question[/]
""",
        "prompt_style": {"prompt": "bold magenta", "prompt.dim": "dim"},
        "colors": {"primary": "magenta", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "fox": {
        "name": "fox",
        "description": "clever tests, zero bugs",
        "animation_speed": 0.0008,
        "panel_style": {"text": "bold bright_red", "border": "bright_red"},
        "banner": r"""
[bold bright_red]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_red]  ▄█▌ (◕‿◕✿) ▐█阄阄[/]
[bold bright_red]  ██▌   🔥 🍂   ▐██[/]
[bold bright_red]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_red]     🍂  🔥  🍂  🔥[/]
[bold white] Test-Agent [bright_red]v{version}[/bright_red][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_red] !help — clever tests, zero bugs[/]
""",
        "prompt_style": {"prompt": "bold bright_red", "prompt.dim": "dim"},
        "colors": {"primary": "bright_red", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "frog": {
        "name": "frog",
        "description": "hop into testing",
        "animation_speed": 0.0006,
        "panel_style": {"text": "bold green", "border": "green"},
        "banner": r"""
[bold green]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold green]  ▄█▌ ( :3 ) ▐█阄阄[/]
[bold green]  ██▌   🺷 💧   ▐██[/]
[bold green]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim green]     💧  🺷  💧  🺷[/]
[bold white] Test-Agent [green]v{version}[/green][/]
[dim] {experts} experts · {skills} skills[/]
[dim green] !help — hop into testing[/]
""",
        "prompt_style": {"prompt": "bold green", "prompt.dim": "dim"},
        "colors": {"primary": "green", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "penguin": {
        "name": "penguin",
        "description": "stay cool, test well",
        "animation_speed": 0.001,
        "panel_style": {"text": "bold bright_cyan", "border": "bright_cyan"},
        "banner": r"""
[bold bright_cyan]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_cyan]  ▄█▌ (°◡°♡) ▐█阄阄[/]
[bold bright_cyan]  ██▌   ❄ 🧊   ▐██[/]
[bold bright_cyan]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_cyan]     🧊  ❄  🧊  ❄[/]
[bold white] Test-Agent [bright_cyan]v{version}[/bright_cyan][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_cyan] !help — stay cool, test well[/]
""",
        "prompt_style": {"prompt": "bold bright_cyan", "prompt.dim": "dim"},
        "colors": {"primary": "bright_cyan", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "bunny": {
        "name": "bunny",
        "description": "hop to quick testing",
        "animation_speed": 0.0004,
        "panel_style": {"text": "bold bright_magenta", "border": "bright_magenta"},
        "banner": r"""
[bold bright_magenta]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_magenta]  ▄█▌ (／.＼) ▐█阄阄[/]
[bold bright_magenta]  ██▌   🥕 🌱   ▐██[/]
[bold bright_magenta]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_magenta]     🌱  🥕  🌱  🥕[/]
[bold white] Test-Agent [bright_magenta]v{version}[/bright_magenta][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_magenta] !help — hop to quick testing[/]
""",
        "prompt_style": {"prompt": "bold bright_magenta", "prompt.dim": "dim"},
        "colors": {"primary": "bright_magenta", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "panda": {
        "name": "panda",
        "description": "take it easy, test well",
        "animation_speed": 0.0011,
        "panel_style": {"text": "bold bright_white", "border": "bright_white"},
        "banner": r"""
[bold bright_white]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_white]  ▄█▌ ㅜ(◕ᵗ◕✿)ノ ▐█阄阄[/]
[bold bright_white]  ██▌   🎋 🎍   ▐██[/]
[bold bright_white]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_white]     🎍  🎋  🎍  🎋[/]
[bold white] Test-Agent [bright_white]v{version}[/bright_white][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_white] !help — take it easy, test well[/]
""",
        "prompt_style": {"prompt": "bold bright_white", "prompt.dim": "dim"},
        "colors": {"primary": "bright_white", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "sunflower": {
        "name": "sunflower",
        "description": "let your tests bloom",
        "animation_speed": 0.0009,
        "panel_style": {"text": "bold bright_yellow", "border": "bright_yellow"},
        "banner": r"""
[bold bright_yellow]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_yellow]  ▄█▌ ✿◕‿◕✿ ▐█阄阄[/]
[bold bright_yellow]  ██▌   🌻 🐝   ▐██[/]
[bold bright_yellow]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_yellow]     🐝  🌻  🐝  🌻[/]
[bold white] Test-Agent [bright_yellow]v{version}[/bright_yellow][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_yellow] !help — let your tests bloom[/]
""",
        "prompt_style": {"prompt": "bold bright_yellow", "prompt.dim": "dim"},
        "colors": {"primary": "bright_yellow", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "cactus": {
        "name": "cactus",
        "description": "resilient testing",
        "animation_speed": 0.0009,
        "panel_style": {"text": "bold green", "border": "green"},
        "banner": r"""
[bold green]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold green]  ▄█▌ (◠‿◠) ▐█阄阄[/]
[bold green]  ██▌   🌵 🌺   ▐██[/]
[bold green]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim green]     🌺  🌵  🌺  🌵[/]
[bold white] Test-Agent [green]v{version}[/green][/]
[dim] {experts} experts · {skills} skills[/]
[dim green] !help — resilient testing[/]
""",
        "prompt_style": {"prompt": "bold green", "prompt.dim": "dim"},
        "colors": {"primary": "green", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "whale": {
        "name": "whale",
        "description": "dive deep into testing",
        "animation_speed": 0.002,
        "panel_style": {"text": "bold bright_blue", "border": "bright_blue"},
        "banner": r"""
[bold bright_blue]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_blue]  ▄█▌ (◉▿◉❀) ▐█阄阄[/]
[bold bright_blue]  ██▌   💧 🐟   ▐██[/]
[bold bright_blue]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_blue]     🐟  💧  🐟  💧[/]
[bold white] Test-Agent [bright_blue]v{version}[/bright_blue][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_blue] !help — dive deep into testing[/]
""",
        "prompt_style": {"prompt": "bold bright_blue", "prompt.dim": "dim"},
        "colors": {"primary": "bright_blue", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "dolphin": {
        "name": "dolphin",
        "description": "leap into quality testing",
        "animation_speed": 0.0004,
        "panel_style": {"text": "bold bright_cyan", "border": "bright_cyan"},
        "banner": r"""
[bold bright_cyan]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_cyan]  ▄█▌ (◕▿◕✿) ▐█阄阄[/]
[bold bright_cyan]  ██▌   💦 〰   ▐██[/]
[bold bright_cyan]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_cyan]     〰  💦  〰  💦[/]
[bold white] Test-Agent [bright_cyan]v{version}[/bright_cyan][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_cyan] !help — leap into quality testing[/]
""",
        "prompt_style": {"prompt": "bold bright_cyan", "prompt.dim": "dim"},
        "colors": {"primary": "bright_cyan", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "turtle": {
        "name": "turtle",
        "description": "steady wins the race",
        "animation_speed": 0.0025,
        "panel_style": {"text": "bold green", "border": "green"},
        "banner": r"""
[bold green]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold green]  ▄█▌ (◉ω◉) ▐█阄阄[/]
[bold green]  ██▌   🌿 🥚   ▐██[/]
[bold green]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim green]     🥚  🌿  🥚  🌿[/]
[bold white] Test-Agent [green]v{version}[/green][/]
[dim] {experts} experts · {skills} skills[/]
[dim green] !help — steady wins the race[/]
""",
        "prompt_style": {"prompt": "bold green", "prompt.dim": "dim"},
        "colors": {"primary": "green", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "octopus": {
        "name": "octopus",
        "description": "eight arms, zero bugs",
        "animation_speed": 0.0004,
        "panel_style": {"text": "bold magenta", "border": "magenta"},
        "banner": r"""
[bold magenta]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold magenta]  ▄█▌ (◉⏠◉) ▐█阄阄[/]
[bold magenta]  ██▌   🺸 🺸   ▐██[/]
[bold magenta]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim magenta]     🺸  🺸  🺸  🺸[/]
[bold white] Test-Agent [magenta]v{version}[/magenta][/]
[dim] {experts} experts · {skills} skills[/]
[dim magenta] !help — eight arms, zero bugs[/]
""",
        "prompt_style": {"prompt": "bold magenta", "prompt.dim": "dim"},
        "colors": {"primary": "magenta", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "eagle": {
        "name": "eagle",
        "description": "soar above the codebase",
        "animation_speed": 0.0012,
        "panel_style": {"text": "bold yellow", "border": "yellow"},
        "banner": r"""
[bold yellow]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold yellow]  ▄█▌ ψ(｀∇｀)ψ ▐█阄阄[/]
[bold yellow]  ██▌   ☀ 🏔   ▐██[/]
[bold yellow]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim yellow]     🏔  ☀  🏔  ☀[/]
[bold white] Test-Agent [yellow]v{version}[/yellow][/]
[dim] {experts} experts · {skills} skills[/]
[dim yellow] !help — soar above the codebase[/]
""",
        "prompt_style": {"prompt": "bold yellow", "prompt.dim": "dim"},
        "colors": {"primary": "yellow", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "butterfly": {
        "name": "butterfly",
        "description": "graceful testing",
        "animation_speed": 0.0007,
        "panel_style": {"text": "bold bright_magenta", "border": "bright_magenta"},
        "banner": r"""
[bold bright_magenta]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_magenta]  ▄█▌ ε(｀ᐧ｀)っ ▐█阄阄[/]
[bold bright_magenta]  ██▌   🌸 🌼   ▐██[/]
[bold bright_magenta]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_magenta]     🌼  🌸  🌼  🌸[/]
[bold white] Test-Agent [bright_magenta]v{version}[/bright_magenta][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_magenta] !help — graceful testing[/]
""",
        "prompt_style": {"prompt": "bold bright_magenta", "prompt.dim": "dim"},
        "colors": {"primary": "bright_magenta", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "parrot": {
        "name": "parrot",
        "description": "repeatable, reliable",
        "animation_speed": 0.0005,
        "panel_style": {"text": "bold bright_green", "border": "bright_green"},
        "banner": r"""
[bold bright_green]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_green]  ▄█▌ (◕⨊◕✿) ▐█阄阄[/]
[bold bright_green]  ██▌   🌴 🍃   ▐██[/]
[bold bright_green]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_green]     🍃  🌴  🍃  🌴[/]
[bold white] Test-Agent [bright_green]v{version}[/bright_green][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_green] !help — repeatable, reliable[/]
""",
        "prompt_style": {"prompt": "bold bright_green", "prompt.dim": "dim"},
        "colors": {"primary": "bright_green", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "dragonfly": {
        "name": "dragonfly",
        "description": "dart, hover, test",
        "animation_speed": 0.0003,
        "panel_style": {"text": "bold bright_cyan", "border": "bright_cyan"},
        "banner": r"""
[bold bright_cyan]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_cyan]  ▄█▌ ⁽⁽ଘ( ˙Ꭓ˙ )ଓ⁾⁾ ▐█阄阄[/]
[bold bright_cyan]  ██▌   🺷 💨   ▐██[/]
[bold bright_cyan]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_cyan]     💨  🺷  💨  🺷[/]
[bold white] Test-Agent [bright_cyan]v{version}[/bright_cyan][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_cyan] !help — dart, hover, test[/]
""",
        "prompt_style": {"prompt": "bold bright_cyan", "prompt.dim": "dim"},
        "colors": {"primary": "bright_cyan", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "lion": {
        "name": "lion",
        "description": "rule your test kingdom",
        "animation_speed": 0.0009,
        "panel_style": {"text": "bold bright_yellow", "border": "bright_yellow"},
        "banner": r"""
[bold bright_yellow]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_yellow]  ▄█▌ ʕ♛ᵥ♛ʔ ▐█阄阄[/]
[bold bright_yellow]  ██▌   👑 🏆   ▐██[/]
[bold bright_yellow]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_yellow]     🏆  👑  🏆  👑[/]
[bold white] Test-Agent [bright_yellow]v{version}[/bright_yellow][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_yellow] !help — rule your test kingdom[/]
""",
        "prompt_style": {"prompt": "bold bright_yellow", "prompt.dim": "dim"},
        "colors": {"primary": "bright_yellow", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "elephant": {
        "name": "elephant",
        "description": "never forget a test",
        "animation_speed": 0.0013,
        "panel_style": {"text": "bold bright_white", "border": "bright_white"},
        "banner": r"""
[bold bright_white]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_white]  ▄█▌ (◕ᵥ◕)っ🎈 ▐█阄阄[/]
[bold bright_white]  ██▌   🌍 📋   ▐██[/]
[bold bright_white]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_white]     📋  🌍  📋  🌍[/]
[bold white] Test-Agent [bright_white]v{version}[/bright_white][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_white] !help — never forget a test[/]
""",
        "prompt_style": {"prompt": "bold bright_white", "prompt.dim": "dim"},
        "colors": {"primary": "bright_white", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "deer": {
        "name": "deer",
        "description": "swift, elegant testing",
        "animation_speed": 0.0007,
        "panel_style": {"text": "bold yellow", "border": "yellow"},
        "banner": r"""
[bold yellow]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold yellow]  ▄█▌ ◌❲●❳◌ ▐█阄阄[/]
[bold yellow]  ██▌   🌲 🍄   ▐██[/]
[bold yellow]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim yellow]     🍄  🌲  🍄  🌲[/]
[bold white] Test-Agent [yellow]v{version}[/yellow][/]
[dim] {experts} experts · {skills} skills[/]
[dim yellow] !help — swift, elegant testing[/]
""",
        "prompt_style": {"prompt": "bold yellow", "prompt.dim": "dim"},
        "colors": {"primary": "yellow", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
    },
    "hedgehog": {
        "name": "hedgehog",
        "description": "catch every edge case",
        "animation_speed": 0.001,
        "panel_style": {"text": "bold bright_black", "border": "bright_black"},
        "banner": r"""
[bold bright_black]    阄阄阄阄阄阄阄阄阄阄阈阈阈阈阈阈[/]
[bold bright_black]  ▄█▌ (◉ᵥ◉)🍄 ▐█阄阄[/]
[bold bright_black]  ██▌   🍂 🌰   ▐██[/]
[bold bright_black]  阀█阄阄阄阄阄阄阄阄阄阄阄阄█阀[/]
[dim bright_black]     🌰  🍂  🌰  🍂[/]
[bold white] Test-Agent [bright_black]v{version}[/bright_black][/]
[dim] {experts} experts · {skills} skills[/]
[dim bright_black] !help — catch every edge case[/]
""",
        "prompt_style": {"prompt": "bold bright_black", "prompt.dim": "dim"},
        "colors": {"primary": "bright_black", "success": "bright_green", "error": "bright_red", "warning": "yellow", "dim": "dim"},
        "icons": {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"},
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
    from runtime.config.settings import get_settings
    skin = get_skin(skin_name)
    return skin["banner"].format(
        version=runtime.__version__,
        experts=_count_md_files(str(get_settings().experts_dir)),
        skills=_count_md_files(str(get_settings().skills_dir)),
    )
