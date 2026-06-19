"""mcp-protocol-adapter MCP server.

Tools: ping (multi-protocol: http/grpc/ws/mqtt/kafka via adapter dispatch),
list_protocols.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from loguru import logger

from runtime.mcp.base import make_server, run_stdio, tool_decision_logged

# trigger adapter registration
from runtime.mcp.protocol_adapter import adapters  # noqa: F401
from runtime.mcp.protocol_adapter.base import REGISTRY, get_adapter


@tool_decision_logged("list_protocols")
async def tool_list_protocols() -> dict:
    return {"protocols": sorted(REGISTRY.keys())}


@tool_decision_logged("ping")
async def tool_ping(protocol: str, target: str, payload: Any = "ping", timeout: float = 10.0) -> dict:
    adapter = get_adapter(protocol)
    result = await adapter.ping(target, payload=payload, timeout=timeout)
    return {
        "protocol": protocol,
        "target": target,
        "ok": result.ok,
        "elapsed_ms": result.elapsed_ms,
        "payload": result.payload if isinstance(result.payload, str | dict | None) else str(result.payload),
        "error": result.error,
        "meta": result.meta,
    }


def build_server():
    try:
        from mcp.types import TextContent, Tool
    except ImportError as e:
        raise RuntimeError("mcp SDK not installed") from e

    server = make_server("protocol-adapter")

    TOOLS = [
        Tool(
            name="list_protocols",
            description="List registered protocol adapters (http/grpc/ws/mqtt/kafka).",
            inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        Tool(
            name="ping",
            description="Generic protocol ping: connect → send → recv → close. Returns elapsed_ms + payload.",
            inputSchema={
                "type": "object",
                "properties": {
                    "protocol": {"type": "string", "enum": sorted(REGISTRY.keys())},
                    "target": {"type": "string", "description": "URL / host:port / broker addr"},
                    "payload": {"description": "string | dict | bytes"},
                    "timeout": {"type": "number", "default": 10.0},
                },
                "required": ["protocol", "target"],
                "additionalProperties": False,
            },
        ),
    ]

    @server.list_tools()
    async def _list_tools():
        return TOOLS

    DISPATCH = {"list_protocols": tool_list_protocols, "ping": tool_ping}

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> list:
        arguments = arguments or {}
        handler = DISPATCH.get(name)
        if handler is None:
            return [TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))]
        try:
            result = await handler(**arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]
        except Exception as e:
            logger.exception("tool {} failed", name)
            return [TextContent(type="text", text=json.dumps({"error": str(e), "tool": name}))]

    return server


def main():
    server = build_server()
    asyncio.run(run_stdio(server))


if __name__ == "__main__":
    main()
