"""Plugin scaffold generator — creates a plugin skeleton directory."""

from __future__ import annotations

from pathlib import Path

import yaml

from sdk.plugin_schema import PluginManifest, PluginType

_MANIFEST_FILENAME = "tagent-plugin.yaml"

_TEMPLATES: dict[str, dict[str, str]] = {
    PluginType.AGENT: {
        "src/__init__.py": (
            '"""Auto-generated Test-Agent agent plugin: {name}."""\n'
            "\n"
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def register():\n"
            '    return {{"name": "{name}", "role": "custom-agent"}}\n'
        ),
        "tests/test_plugin.py": (
            '"""Tests for agent plugin: {name}."""\n'
            "\n"
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def test_register_returns_dict():\n"
            "    from tagent_{safe_name}.src import register\n"
            "    result = register()\n"
            '    assert result["name"] == "{name}"\n'
        ),
        "README.md": (
            "# {name}\n\n"
            "{description}\n\n"
            "## Usage\n\n"
            "This plugin registers a custom agent with Test-Agent.\n"
        ),
    },
    PluginType.SKILL: {
        "src/__init__.py": (
            '"""Auto-generated Test-Agent skill plugin: {name}."""\n'
            "\n"
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def register():\n"
            '    return {{"name": "{name}", "role": "custom-skill", "description": "{description}"}}\n'
        ),
        "tests/test_plugin.py": (
            '"""Tests for skill plugin: {name}."""\n'
            "\n"
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def test_register_returns_dict():\n"
            "    from tagent_{safe_name}.src import register\n"
            "    result = register()\n"
            '    assert result["name"] == "{name}"\n'
        ),
        "README.md": (
            "# {name}\n\n"
            "{description}\n\n"
            "## Usage\n\n"
            "This plugin registers a custom skill with Test-Agent.\n"
        ),
    },
    PluginType.TOOL: {
        "src/__init__.py": (
            '"""Auto-generated Test-Agent tool plugin: {name}."""\n'
            "\n"
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def register():\n"
            '    return {{"name": "{name}", "role": "custom-tool"}}\n'
        ),
        "tests/test_plugin.py": (
            '"""Tests for tool plugin: {name}."""\n'
            "\n"
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def test_register_returns_dict():\n"
            "    from tagent_{safe_name}.src import register\n"
            "    result = register()\n"
            '    assert result["name"] == "{name}"\n'
        ),
        "README.md": (
            "# {name}\n\n"
            "{description}\n\n"
            "## Usage\n\n"
            "This plugin registers a custom tool with Test-Agent.\n"
        ),
    },
    PluginType.GATE: {
        "src/__init__.py": (
            '"""Auto-generated Test-Agent gate plugin: {name}."""\n'
            "\n"
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def register():\n"
            '    return {{"name": "{name}", "role": "custom-gate"}}\n'
        ),
        "tests/test_plugin.py": (
            '"""Tests for gate plugin: {name}."""\n'
            "\n"
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def test_register_returns_dict():\n"
            "    from tagent_{safe_name}.src import register\n"
            "    result = register()\n"
            '    assert result["name"] == "{name}"\n'
        ),
        "README.md": (
            "# {name}\n\n"
            "{description}\n\n"
            "## Usage\n\n"
            "This plugin registers a custom quality gate with Test-Agent.\n"
        ),
    },
    PluginType.PROFILE: {
        "src/__init__.py": (
            '"""Auto-generated Test-Agent profile plugin: {name}."""\n'
            "\n"
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def register():\n"
            '    return {{"name": "{name}", "role": "custom-profile"}}\n'
        ),
        "tests/test_plugin.py": (
            '"""Tests for profile plugin: {name}."""\n'
            "\n"
            "from __future__ import annotations\n"
            "\n"
            "\n"
            "def test_register_returns_dict():\n"
            "    from tagent_{safe_name}.src import register\n"
            "    result = register()\n"
            '    assert result["name"] == "{name}"\n'
        ),
        "README.md": (
            "# {name}\n\n"
            "{description}\n\n"
            "## Usage\n\n"
            "This plugin registers a custom compliance profile with Test-Agent.\n"
        ),
    },
}


def scaffold_plugin(
    name: str,
    plugin_type: str,
    output_dir: Path,
    *,
    description: str = "",
    author: str = "",
    version: str = "1.0.0",
) -> Path:
    """Generate a plugin skeleton directory.

    Creates:
        {name}/
          tagent-plugin.yaml    (plugin manifest)
          src/__init__.py       (plugin entry point)
          tests/test_plugin.py  (starter test)
          README.md             (usage docs)

    Returns the path to the created plugin directory.
    """
    if plugin_type not in (pt.value for pt in PluginType):
        raise ValueError(f"Unknown plugin_type '{plugin_type}'. Must be one of: {', '.join(pt.value for pt in PluginType)}")

    ptype = PluginType(plugin_type)
    safe_name = name.replace("-", "_").replace(".", "_")
    plugin_dir = output_dir / name
    plugin_dir.mkdir(parents=True, exist_ok=True)

    manifest = PluginManifest(
        name=name,
        version=version,
        description=description or f"Plugin: {name}",
        author=author or "anonymous",
        plugin_type=ptype,
    )

    manifest_path = plugin_dir / _MANIFEST_FILENAME
    # Use mode="json" to serialise enum values as plain strings, not Python tags
    manifest_path.write_text(
        yaml.dump(manifest.model_dump(mode="json"), default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    templates = _TEMPLATES.get(ptype, _TEMPLATES[PluginType.SKILL])
    for rel_path, content_template in templates.items():
        file_path = plugin_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        content = content_template.format(name=name, safe_name=safe_name, description=manifest.description)
        file_path.write_text(content, encoding="utf-8")

    return plugin_dir
