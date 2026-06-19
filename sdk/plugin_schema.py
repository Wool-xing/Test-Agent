"""Plugin manifest — Pydantic model for tagent-plugin.yaml."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PluginType(str, Enum):
    AGENT = "agent"
    SKILL = "skill"
    TOOL = "tool"
    GATE = "gate"
    PROFILE = "profile"


class PluginManifest(BaseModel):
    """Plugin manifest schema (tagent-plugin.yaml)."""

    name: str = Field(description="Unique plugin ID, e.g. 'tagent-jira'")
    version: str = Field(default="1.0.0", description="Semver")
    description: str
    author: str
    license: str = "MIT"
    plugin_type: PluginType
    entry_point: str | None = Field(default=None, description="Python import path for Python plugins")
    wasm_path: str | None = Field(default=None, description="Path to .wasm for WASM plugins")
    mcp_server: str | None = Field(default=None, description="MCP server name for MCP plugins")
    dependencies: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    min_tagent_version: str = "2.0.0"
