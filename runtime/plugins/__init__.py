"""Plugin hot-loader — drop-in plugins from plugins/ directory (P3 #22).

Place .py files in workspace/plugins/ and they auto-load on startup.
Each plugin exports: register() -> dict {name, description, run(text) -> str}
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def discover_plugins(plugins_dir: Path | None = None) -> dict[str, Any]:
    """Scan plugins directory and load all .py files. Returns {name: module}."""
    if plugins_dir is None:
        plugins_dir = Path(__file__).resolve().parents[2] / "workspace" / "plugins"

    if not plugins_dir.is_dir():
        return {}

    loaded: dict[str, Any] = {}
    for f in sorted(plugins_dir.glob("*.py")):
        if f.name.startswith("_"):
            continue
        name = f.stem
        try:
            spec = importlib.util.spec_from_file_location(f"plugin_{name}", str(f))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                sys.modules[f"plugin_{name}"] = mod
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    loaded[name] = mod
        except Exception:
            pass  # skip broken plugins
    return loaded
