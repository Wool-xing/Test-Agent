"""tagent skill — Skill lifecycle commands (Sprint 3: 扩展体系).

Commands:
    tagent skill list              — list installed skills
    tagent skill search <keyword>  — search by name/tag/description
"""

from __future__ import annotations

import typer
from pathlib import Path

from runtime.registry.registry import build_catalog

app = typer.Typer(name="skill", help="Manage Skills — install, list, search, test")


@app.command("list")
def skill_list() -> None:
    """List all installed skills (built-in + SDK registered)."""
    cat = build_catalog()
    if not cat.skills:
        print("No skills installed.")
        return

    print(f"{'Name':<30} {'Description':<50}")
    print("-" * 80)
    for name, entry in sorted(cat.skills.items()):
        desc = entry.description[:47] + "..." if len(entry.description) > 50 else entry.description
        print(f"{name:<30} {desc:<50}")


@app.command("search")
def skill_search(keyword: str = typer.Argument(..., help="Keyword to search in skill names and descriptions")) -> None:
    """Search installed skills by keyword."""
    cat = build_catalog()
    matches = [
        (name, entry) for name, entry in cat.skills.items()
        if keyword.lower() in name.lower() or keyword.lower() in entry.description.lower()
    ]
    if not matches:
        print(f"No skills found matching '{keyword}'.")
        return

    print(f"Skills matching '{keyword}':")
    for name, entry in sorted(matches):
        print(f"  {name} — {entry.description[:80]}")
