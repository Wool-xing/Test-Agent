"""Tests for Plugin SDK: schema validation + scaffold generation."""

from __future__ import annotations

import tempfile
import json
from pathlib import Path

import pytest
import yaml

from sdk.plugin_schema import PluginManifest, PluginType
from sdk.scaffold import scaffold_plugin


class TestPluginManifest:
    """Unit tests for PluginManifest Pydantic model."""

    def test_minimal_valid_manifest(self):
        """Minimal required fields should create a valid manifest."""
        pm = PluginManifest(
            name="test-plugin",
            description="A test plugin",
            author="me",
            plugin_type="skill",
        )
        assert pm.name == "test-plugin"
        assert pm.version == "1.0.0"
        assert pm.description == "A test plugin"
        assert pm.author == "me"
        assert pm.plugin_type == PluginType.SKILL
        assert pm.license == "MIT"
        assert pm.dependencies == []
        assert pm.tags == []
        assert pm.min_tagent_version == "2.0.0"
        assert pm.entry_point is None
        assert pm.wasm_path is None
        assert pm.mcp_server is None

    def test_all_fields_populated(self):
        """All optional fields should be accepted."""
        pm = PluginManifest(
            name="full-plugin",
            version="2.1.0",
            description="A full-featured plugin",
            author="team",
            license="Apache-2.0",
            plugin_type="agent",
            entry_point="tagent_full_plugin.src:register",
            wasm_path="./plugin.wasm",
            mcp_server="my-mcp-server",
            dependencies=["pydantic", "yaml"],
            tags=["testing", "agent"],
            min_tagent_version="2.1.0",
        )
        assert pm.name == "full-plugin"
        assert pm.version == "2.1.0"
        assert pm.plugin_type == PluginType.AGENT
        assert pm.entry_point == "tagent_full_plugin.src:register"
        assert pm.wasm_path == "./plugin.wasm"
        assert pm.mcp_server == "my-mcp-server"
        assert pm.dependencies == ["pydantic", "yaml"]
        assert pm.tags == ["testing", "agent"]
        assert pm.min_tagent_version == "2.1.0"

    def test_missing_required_fields_raises(self):
        """Missing name should raise validation error."""
        with pytest.raises(Exception):
            PluginManifest(description="no name", author="me", plugin_type="skill")

    def test_invalid_plugin_type_raises(self):
        """Invalid plugin_type should raise validation error."""
        with pytest.raises(Exception):
            PluginManifest(
                name="bad",
                description="bad type",
                author="me",
                plugin_type="invalid_type",  # type: ignore[arg-type]
            )

    def test_model_dump_excludes_none(self):
        """model_dump should serialize but keep None fields."""
        pm = PluginManifest(
            name="test",
            description="desc",
            author="me",
            plugin_type="tool",
        )
        d = pm.model_dump()
        assert d["name"] == "test"
        assert d["entry_point"] is None
        # JSON serializable round-trip
        text = json.dumps(d)
        reloaded = json.loads(text)
        assert reloaded["name"] == "test"


class TestScaffolder:
    """Integration tests for scaffold_plugin function."""

    def test_scaffold_creates_directory_structure(self, tmp_path: Path):
        """Scaffold should create plugin dir with manifest, src, tests, README."""
        plugin_dir = scaffold_plugin("my-test-plugin", "skill", tmp_path)

        assert plugin_dir.exists()
        assert plugin_dir.is_dir()
        assert plugin_dir.name == "my-test-plugin"

        # Check created files
        manifest = plugin_dir / "tagent-plugin.yaml"
        assert manifest.exists()

        src_init = plugin_dir / "src" / "__init__.py"
        assert src_init.exists()

        test_file = plugin_dir / "tests" / "test_plugin.py"
        assert test_file.exists()

        readme = plugin_dir / "README.md"
        assert readme.exists()

    def test_scaffold_manifest_is_valid(self, tmp_path: Path):
        """Scaffolded manifest should parse as valid PluginManifest."""
        plugin_dir = scaffold_plugin("valid-plugin", "agent", tmp_path)

        manifest_path = plugin_dir / "tagent-plugin.yaml"
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

        pm = PluginManifest(**raw)
        assert pm.name == "valid-plugin"
        assert pm.plugin_type == PluginType.AGENT

    def test_scaffold_all_plugin_types(self, tmp_path: Path):
        """Every plugin type should scaffold without error."""
        for pt in PluginType:
            plugin_dir = scaffold_plugin(f"test-{pt.value}", pt.value, tmp_path)

            manifest_path = plugin_dir / "tagent-plugin.yaml"
            raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            pm = PluginManifest(**raw)
            assert pm.plugin_type == pt

            src_init = plugin_dir / "src" / "__init__.py"
            content = src_init.read_text(encoding="utf-8")
            assert "def register():" in content

            test_file = plugin_dir / "tests" / "test_plugin.py"
            test_content = test_file.read_text(encoding="utf-8")
            assert "def test_register_returns_dict" in test_content

            readme = plugin_dir / "README.md"
            readme_content = readme.read_text(encoding="utf-8")
            assert readme_content.startswith(f"# test-{pt.value}")

    def test_scaffold_invalid_type_raises(self, tmp_path: Path):
        """Unknown plugin_type should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown plugin_type"):
            scaffold_plugin("bad", "bogus", tmp_path)

    def test_scaffold_custom_description_and_author(self, tmp_path: Path):
        """Custom description and author should appear in manifest."""
        plugin_dir = scaffold_plugin(
            "custom",
            "skill",
            tmp_path,
            description="My custom skill",
            author="John Doe",
        )

        manifest_path = plugin_dir / "tagent-plugin.yaml"
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        assert raw["description"] == "My custom skill"
        assert raw["author"] == "John Doe"
