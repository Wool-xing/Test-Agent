"""plugin: scaffold + validate + install + list + uninstall plugin commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from runtime.cli._shared import console

plugin_app = typer.Typer(add_completion=False, help="Plugin management: scaffold, validate, install, list, uninstall")


def register(app: typer.Typer) -> None:
    """Register plugin_app as 'plugin' sub-command group."""
    app.add_typer(plugin_app, name="plugin")


@plugin_app.command()
def new(
    name: str = typer.Argument(..., help="Plugin name (e.g. 'tagent-jira')"),
    plugin_type: str = typer.Option("skill", "--type", "-t", help="agent | skill | tool | gate | profile"),
    output_dir: str = typer.Option(".", "--output-dir", "-o", help="Output directory"),
    description: str = typer.Option("", "--description", "-d", help="Plugin description"),
    author: str = typer.Option("", "--author", "-a", help="Plugin author"),
):
    """Scaffold a new plugin skeleton."""
    from sdk.scaffold import scaffold_plugin

    out = Path(output_dir).resolve()
    try:
        plugin_dir = scaffold_plugin(name, plugin_type, out, description=description, author=author)
    except ValueError as e:
        console.print(f"[red]Error:[/] {e}")
        raise typer.Exit(2)

    console.print(f"[green]Plugin scaffolded[/] → {plugin_dir}")
    console.print(f"  manifest: {plugin_dir / 'tagent-plugin.yaml'}")
    console.print(f"  source:   {plugin_dir / 'src' / '__init__.py'}")
    console.print(f"  tests:    {plugin_dir / 'tests' / 'test_plugin.py'}")
    console.print(f"  docs:     {plugin_dir / 'README.md'}")


@plugin_app.command()
def validate(
    path: str = typer.Argument(".", help="Path to plugin directory or manifest file"),
):
    """Validate a plugin manifest (tagent-plugin.yaml)."""
    from sdk.plugin_schema import PluginManifest

    p = Path(path).resolve()
    if p.is_dir():
        manifest_path = p / "tagent-plugin.yaml"
    else:
        manifest_path = p

    if not manifest_path.exists():
        console.print(f"[red]Manifest not found:[/] {manifest_path}")
        raise typer.Exit(2)

    import yaml
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        console.print(f"[red]YAML parse error:[/] {e}")
        raise typer.Exit(1)

    if raw is None:
        console.print(f"[red]Empty manifest:[/] {manifest_path}")
        raise typer.Exit(1)

    try:
        manifest = PluginManifest(**raw)
    except Exception as e:
        console.print(f"[red]Validation failed:[/] {e}")
        raise typer.Exit(1)

    console.print(f"[green]Valid[/] {manifest.name} v{manifest.version} ({manifest.plugin_type.value})")
    for field in ("description", "author", "license", "min_tagent_version"):
        val = getattr(manifest, field)
        if val:
            console.print(f"  {field}: {val}")
    if manifest.dependencies:
        console.print(f"  dependencies: {', '.join(manifest.dependencies)}")
    if manifest.tags:
        console.print(f"  tags: {', '.join(manifest.tags)}")


@plugin_app.command()
def install(
    name: str = typer.Argument(..., help="Plugin name to install"),
    version: str = typer.Option(None, "--version", help="Specific version to install"),
):
    """Install a plugin from marketplace."""
    from runtime.marketplace.catalog import find as catalog_find

    entry = catalog_find(name)
    if entry is None:
        console.print(f"[yellow]Plugin '{name}' not found in marketplace registry.[/]")
        console.print("Use [cyan]tagent plugin new[/] to scaffold a new plugin, then [cyan]tagent market install[/] to install from source.")
        return

    console.print(f"Found {name} v{entry.version} in {entry.lane} lane.")
    console.print("Use [cyan]tagent market install {name} <lane> --source <path>[/] to install.")


@plugin_app.command(name="list")
def list_installed():
    """List installed plugins."""
    from runtime.marketplace.catalog import load_local

    entries = load_local()
    if not entries:
        console.print("[yellow]No plugins installed.[/]")
        return

    t = Table(title="Installed Plugins")
    for col in ("name", "lane", "version", "tier", "installed_at"):
        t.add_column(col)
    for e in entries:
        t.add_row(e.name, e.lane, e.version, e.source_tier, e.installed_at or "--")
    console.print(t)


@plugin_app.command()
def uninstall(
    name: str = typer.Argument(..., help="Plugin name to uninstall"),
):
    """Uninstall a plugin (archive only, irreversible)."""
    from runtime.marketplace.installer import uninstall as do_uninstall

    res = do_uninstall(name)
    if res["ok"]:
        console.print(f"[yellow]Archived[/] {name} → {res['archived_to']}")
    else:
        console.print(f"[red]Failed:[/] {res.get('error')}")
        raise typer.Exit(1)
