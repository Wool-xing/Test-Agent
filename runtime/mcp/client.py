"""MCP client — connect to external MCP servers, discover tools, call tools.

Uses the Python MCP SDK's client-side API to establish stdio connections
to local MCP servers configured in config/.mcp.json. Provides a unified
interface for agents and skills to use MCP tools at runtime.
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class McpTool:
    """Discovered MCP tool metadata."""
    server_name: str
    tool_name: str
    description: str = ""
    input_schema: dict = field(default_factory=dict)


@dataclass
class McpToolResult:
    """Result of calling an MCP tool."""
    ok: bool
    server_name: str
    tool_name: str
    content: str = ""
    error: str | None = None


def _find_config() -> Path | None:
    """Locate the .mcp.json config file."""
    from runtime.config.settings import get_settings
    candidates = [
        get_settings().config_dir / ".mcp.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _parse_config(path: Path) -> dict[str, dict]:
    """Parse .mcp.json and return enabled server configurations.

    Returns merged {name: {command, args, description}} dict.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to parse .mcp.json: {}", e)
        return {}

    servers: dict[str, dict] = {}
    # Main servers section
    for name, cfg in data.get("mcpServers", {}).items():
        if isinstance(cfg, dict) and "command" in cfg:
            servers[name] = cfg
    # Also include pending servers (available but not yet active)
    pending = data.get("_pending_servers_v1_2_0_alpha", {})
    for name, cfg in pending.items():
        if isinstance(cfg, dict) and "command" in cfg and name not in servers:
            servers[name] = cfg

    return servers


class McpClient:
    """Connects to local MCP servers, discovers tools, and calls them.

    Usage:
        client = McpClient()
        tools = await client.list_all_tools()
        result = await client.call_tool("test-orchestrator", "catalog", {})
        await client.disconnect()
    """

    def __init__(self, config_path: Path | None = None):
        self._config_path = config_path or _find_config()
        self._connections: dict[str, Any] = {}  # server_name -> (read, write, session)

    @property
    def servers(self) -> dict[str, dict]:
        """Return configured server metadata."""
        if self._config_path is None:
            return {}
        return _parse_config(self._config_path)

    async def list_all_tools(self) -> list[McpTool]:
        """Discover tools from all configured MCP servers. Connects as needed."""
        tools: list[McpTool] = []
        for name in self.servers:
            try:
                server_tools = await self.list_tools(name)
                tools.extend(server_tools)
            except Exception as exc:
                logger.warning("Failed to list tools from MCP server '{}': {}", name, exc)
        return tools

    def _make_server_params(self, server_name: str):
        """Build StdioServerParameters from config."""
        from mcp.client.stdio import StdioServerParameters

        cfg = self.servers.get(server_name)
        if cfg is None:
            raise KeyError(f"Unknown MCP server: {server_name}. Available: {sorted(self.servers)}")

        command = cfg["command"]
        args = list(cfg.get("args", []))

        # Resolve ${PROJECT_ROOT} in args
        resolved_args = []
        for a in args:
            if "${PROJECT_ROOT}" in a:
                root = str(Path(__file__).resolve().parents[2])
                a = a.replace("${PROJECT_ROOT}", root)
            resolved_args.append(a)

        return StdioServerParameters(command=command, args=resolved_args)


    async def list_tools(self, server_name: str) -> list[McpTool]:
        """Discover tools from a specific MCP server."""
        try:
            from mcp.client.stdio import stdio_client
            from mcp import ClientSession
        except ImportError as e:
            raise RuntimeError("mcp SDK client not available; pip install mcp") from e

        params = self._make_server_params(server_name)
        tools: list[McpTool] = []

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                for t in (result.tools if hasattr(result, 'tools') else []):
                    tools.append(McpTool(
                        server_name=server_name,
                        tool_name=t.name,
                        description=getattr(t, 'description', '') or '',
                        input_schema=getattr(t, 'inputSchema', {}) or {},
                    ))

        return tools

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: dict | None = None
    ) -> McpToolResult:
        """Call a tool on a remote MCP server. Connects, calls, and disconnects per invocation."""
        try:
            from mcp.client.stdio import stdio_client
            from mcp import ClientSession
        except ImportError as e:
            raise RuntimeError("mcp SDK client not available; pip install mcp") from e

        try:
            params = self._make_server_params(server_name)
        except KeyError as e:
            return McpToolResult(
                ok=False, server_name=server_name, tool_name=tool_name, error=str(e),
            )

        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments or {})

                    # Extract text content from result
                    parts: list[str] = []
                    for c in (result.content if hasattr(result, 'content') else []):
                        if hasattr(c, 'text'):
                            parts.append(c.text)
                    content = "\n".join(parts)

                    return McpToolResult(
                        ok=True, server_name=server_name, tool_name=tool_name, content=content,
                    )
        except Exception as exc:
            logger.warning("MCP tool call {}/{} failed: {}", server_name, tool_name, exc)
            return McpToolResult(
                ok=False, server_name=server_name, tool_name=tool_name, error=str(exc),
            )

    async def disconnect(self) -> None:
        """Close all active connections. No-op — stdio_client handles cleanup via context manager."""
        self._connections.clear()


# ── singleton convenience ─────────────────────────────────────────────


_client: McpClient | None = None


def get_client() -> McpClient:
    """Return a shared McpClient instance (lazy init)."""
    global _client
    if _client is None:
        _client = McpClient()
    return _client
