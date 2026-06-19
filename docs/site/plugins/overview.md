# Plugins

Test-Agent V2 supports a plugin marketplace powered by Python's `importlib.metadata` entry points system (Phase 8, #34). Plugins can register agents, skills, and backends.

## Discovery

Plugins are discovered automatically at startup via the `tagent` entry point group:

```python
# runtime/marketplace/discovery.py
from importlib.metadata import entry_points

def discover_plugins():
    eps = entry_points(group="tagent")
    for ep in eps:
        # ep.name: plugin name
        # ep.value: import path
        ...
```

## Creating a Plugin

### 1. Package Structure

```
my-tagent-plugin/
  pyproject.toml
  my_plugin/
    __init__.py
    agents.py
    skills.py
```

### 2. Register Entry Points

In `pyproject.toml`:

```toml
[project.entry-points.tagent]
agents = "my_plugin.agents:register"
skills = "my_plugin.skills:register"
```

### 3. Implement Registration

```python
# my_plugin/agents.py
def register():
    return {
        "my-custom-agent": {
            "name": "My Custom Agent",
            "description": "A custom testing agent",
            "prompt_path": "my_plugin/prompts/agent.md"
        }
    }
```

## Plugin Types

### Agents

Register custom AI agents that extend the 16 built-in experts. Agents are prompt-based and follow the same `.md` format as `ai/agents/`.

### Skills

Register custom skill workflows. Skills define step-by-step agent call sequences and follow the format in `ai/skills/`.

### Backends

Register custom execution backends (e.g., a Kubernetes runner or a cloud VM launcher). Backends implement the `runtime/backends/` protocol.

## Listing Installed Plugins

```bash
tagent catalog --plugins
```

Shows all discovered plugins alongside built-in agents and skills.

## Marketplace

The deploy marketplace (`deploy/marketplace/`) serves as a registry of known community plugins. To add your plugin:

1. Publish your package to PyPI with the `tagent` entry point
2. Submit a PR adding your plugin metadata to `deploy/marketplace/`
3. Tag your package with `tagent-plugin` on PyPI
