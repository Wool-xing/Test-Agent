"""Test-Agent Plugin SDK — v1.

Plugins extend Test-Agent with custom agents, skills, tools, gates, and profiles.
"""

from __future__ import annotations

from sdk.plugin_schema import PluginManifest, PluginType
from sdk.scaffold import scaffold_plugin

__all__ = ["PluginManifest", "PluginType", "scaffold_plugin"]
