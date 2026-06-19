"""specs — Manifest schema and gate definitions for Test-Agent.

This package is the single-source-of-truth for agent and skill definitions.
"""

from __future__ import annotations

from specs.manifest import Backend, Kind, ManifestV2, validate_manifest

__all__ = ["Backend", "Kind", "ManifestV2", "validate_manifest"]
