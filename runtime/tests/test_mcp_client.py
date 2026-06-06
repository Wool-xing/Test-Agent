"""TDD: MCP client — config parsing, tool discovery, tool calling."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


class TestConfigParsing:
    """Test .mcp.json config file parsing."""

    def test_parse_valid_config(self):
        from runtime.mcp.client import _parse_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "mcpServers": {
                    "test-server": {
                        "command": "python",
                        "args": ["-m", "test.module"],
                        "description": "Test MCP server"
                    }
                }
            }, f)
            path = Path(f.name)

        try:
            servers = _parse_config(path)
            assert "test-server" in servers
            assert servers["test-server"]["command"] == "python"
            assert servers["test-server"]["args"] == ["-m", "test.module"]
        finally:
            path.unlink()

    def test_parse_pending_servers(self):
        from runtime.mcp.client import _parse_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "mcpServers": {},
                "_pending_servers_v1_2_0_alpha": {
                    "pending-server": {
                        "command": "python",
                        "args": ["-m", "pending.module"],
                    }
                }
            }, f)
            path = Path(f.name)

        try:
            servers = _parse_config(path)
            assert "pending-server" in servers
        finally:
            path.unlink()

    def test_parse_empty_config(self):
        from runtime.mcp.client import _parse_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({}, f)
            path = Path(f.name)

        try:
            servers = _parse_config(path)
            assert servers == {}
        finally:
            path.unlink()

    def test_missing_file(self):
        from runtime.mcp.client import _parse_config

        servers = _parse_config(Path("/nonexistent/path.json"))
        assert servers == {}


class TestMcpClient:
    """Test McpClient server listing and tool discovery."""

    def test_client_loads_servers(self):
        from runtime.mcp.client import McpClient

        client = McpClient()
        servers = client.servers
        assert "test-orchestrator" in servers
        assert servers["test-orchestrator"]["command"] == "python"

    def test_client_all_7_servers(self):
        from runtime.mcp.client import McpClient

        client = McpClient()
        servers = client.servers
        # All 7 servers should be in the unified config
        expected = {
            "filesystem", "test-orchestrator", "protocol-adapter",
            "evidence-vault", "defect-tracker", "knowledge-base",
            "compliance-checker",
        }
        assert set(servers.keys()) == expected

    @pytest.mark.asyncio
    async def test_list_tools_test_orchestrator(self):
        from runtime.mcp.client import McpClient

        client = McpClient()
        tools = await client.list_tools("test-orchestrator")
        assert len(tools) >= 1
        tool_names = {t.tool_name for t in tools}
        assert "catalog" in tool_names
        assert all(t.server_name == "test-orchestrator" for t in tools)

    @pytest.mark.asyncio
    async def test_call_catalog_tool(self):
        from runtime.mcp.client import McpClient

        client = McpClient()
        result = await client.call_tool("test-orchestrator", "catalog", {})
        assert result.ok
        assert len(result.content) > 0
        # Catalog should mention experts
        assert "expert" in result.content.lower() or "test-lead" in result.content

    @pytest.mark.asyncio
    async def test_call_unknown_server(self):
        from runtime.mcp.client import McpClient

        client = McpClient()
        result = await client.call_tool("nonexistent-server", "test", {})
        assert not result.ok
        assert "Unknown MCP server" in result.error

    @pytest.mark.asyncio
    async def test_list_all_tools(self):
        from runtime.mcp.client import McpClient

        client = McpClient()
        tools = await client.list_all_tools()
        assert len(tools) >= 5  # at minimum test-orchestrator's 5 tools
        # Should include tools from test-orchestrator
        test_tools = [t for t in tools if t.server_name == "test-orchestrator"]
        assert len(test_tools) >= 1


class TestMcpClientHelpers:
    """Test helper functions."""

    def test_make_server_params(self):
        from runtime.mcp.client import McpClient

        client = McpClient()
        params = client._make_server_params("test-orchestrator")
        assert params.command == "python"
        assert "-m" in params.args
        assert "runtime.mcp.test_orchestrator.server" in params.args

    def test_unknown_server_raises(self):
        from runtime.mcp.client import McpClient

        client = McpClient()
        with pytest.raises(KeyError):
            client._make_server_params("nonexistent-server")


class TestMcpToolResult:
    """Test McpToolResult dataclass."""

    def test_ok_result(self):
        from runtime.mcp.client import McpToolResult

        r = McpToolResult(ok=True, server_name="srv", tool_name="tool", content="result text")
        assert r.ok
        assert r.content == "result text"
        assert r.error is None

    def test_error_result(self):
        from runtime.mcp.client import McpToolResult

        r = McpToolResult(ok=False, server_name="srv", tool_name="tool", error="something went wrong")
        assert not r.ok
        assert r.content == ""
        assert r.error == "something went wrong"
