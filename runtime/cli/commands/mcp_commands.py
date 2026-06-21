"""tagent mcp — MCP Server management commands (Sprint 3)."""

from __future__ import annotations

import asyncio

import typer

app = typer.Typer(name="mcp", help="Manage MCP servers — list, connect, discover tools")


@app.command("list")
def mcp_list() -> None:
    """List configured MCP servers and their available tools."""
    from runtime.mcp.client import get_client

    try:
        client = get_client()
    except Exception as exc:
        print(f"Error loading MCP configuration: {exc}")
        return

    servers = client.servers
    if not servers:
        print("No MCP servers configured.")
        print("Add servers to .mcp.json or config/.mcp.json to get started.")
        return

    for name, cfg in sorted(servers.items()):
        cmd = cfg.get("command", "?")
        print(f"\n{name} ({cmd})")

        try:
            tools = asyncio.run(client.list_tools(name))
        except Exception:
            print("  (server not reachable — start it and try again)")
            continue

        if not tools:
            print("  (no tools discovered)")
        for tool in tools:
            desc = tool.description[:60] + "..." if len(tool.description) > 60 else tool.description
            print(f"  - {tool.tool_name}: {desc}")


@app.command("info")
def mcp_info(server: str = typer.Argument(..., help="Server name from .mcp.json")) -> None:
    """Show detailed information about a specific MCP server."""
    from runtime.mcp.client import get_client

    try:
        client = get_client()
    except Exception as exc:
        print(f"Error: {exc}")
        return

    cfg = client.servers.get(server)
    if not cfg:
        print(f"Server '{server}' not found in configuration.")
        return

    print(f"Server: {server}")
    print(f"Command: {cfg.get('command', '?')}")
    if "args" in cfg:
        print(f"Args: {' '.join(cfg['args'])}")
    if "env" in cfg:
        print("Environment:")
        for k, v in cfg["env"].items():
            masked = v[:4] + "***" if len(v) > 8 else "***"
            print(f"  {k}={masked}")

    try:
        tools = asyncio.run(client.list_tools(server))
        print(f"\nTools ({len(tools)}):")
        for tool in tools:
            print(f"  {tool.tool_name}")
            if tool.description:
                print(f"    {tool.description}")
    except Exception as exc:
        print(f"\nConnection failed: {exc}")
