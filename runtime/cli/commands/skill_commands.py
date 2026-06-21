"""tagent skill — Skill lifecycle commands (Sprint 3: 扩展体系).

Commands:
    tagent skill install <path>    — install a skill from a local directory
    tagent skill list              — list installed skills
    tagent skill search <keyword>  — search by name/tag/description
    tagent skill test <name>       — run a skill's self-tests
"""

from __future__ import annotations

from pathlib import Path

import typer

from runtime.registry.registry import build_catalog

app = typer.Typer(name="skill", help="Manage Skills — install, list, search, test")


@app.command("install")
def skill_install(
    source: str = typer.Argument(..., help="Path to skill source directory"),
    workspace: str = typer.Option("workspace", "--workspace", "-w", help="Workspace root directory"),
) -> None:
    """Install a skill from a local directory into the workspace.

    The source directory must contain a valid SKILL.md with YAML frontmatter.
    Skill names must be kebab-case (lowercase letters, digits, and hyphens).
    """
    from runtime.sdk.install import install_skill

    src = Path(source).resolve()
    ws = Path(workspace).resolve()
    result = install_skill(src, ws)
    if result.ok:
        print(f"Installed '{src.name}' to {result.target_path}")
    else:
        print(f"Error: {result.error}")
        raise typer.Exit(code=1)


@app.command("test")
def skill_test(
    name: str = typer.Argument(..., help="Name of the installed skill to test"),
    workspace: str = typer.Option("workspace", "--workspace", "-w", help="Workspace root directory"),
) -> None:
    """Run self-tests for an installed skill."""
    from runtime.sdk.test_runner import run_skill_tests

    ws = Path(workspace).resolve()
    result = run_skill_tests(name, ws / "skills")
    if not result.ok:
        print(f"Error: {result.error}")
        raise typer.Exit(code=1)
    print(f"Test results for '{name}': {result.passed} passed, {result.failed} failed, {result.total} total")
    if result.failed > 0:
        raise typer.Exit(code=1)


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
