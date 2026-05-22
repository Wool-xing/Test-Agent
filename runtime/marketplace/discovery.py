"""Plugin discovery via importlib.metadata entry_points.

Enables third‑party packages to register agents / skills / backends.

Convention:
    [project.entry-points."tagent"]
    agents = "my_package.agents"
    skills = "my_package.skills"
    backends = "my_package.backends"
"""

from __future__ import annotations

import logging
from importlib.metadata import EntryPoint, entry_points

logger = logging.getLogger(__name__)

PLUGIN_GROUP = "tagent"


def discover_plugins() -> dict[str, list[EntryPoint]]:
    """Discover all registered tagent plugins grouped by type.

    Returns: {"agents": [...], "skills": [...], "backends": [...]}
    """
    discovered: dict[str, list[EntryPoint]] = {"agents": [], "skills": [], "backends": []}
    try:
        eps = entry_points(group=PLUGIN_GROUP)
        for ep in eps:
            # ep.name = "agents" / "skills" / "backends"
            kind = ep.name
            if kind in discovered:
                discovered[kind].append(ep)
        if any(discovered.values()):
            logger.info(f"plugins discovered: {sum(len(v) for v in discovered.values())} total")
    except TypeError:
        # Python < 3.12 — entry_points() without group filter returns all
        try:
            all_eps = entry_points()
            for ep in all_eps:
                if ep.group == PLUGIN_GROUP and ep.name in discovered:
                    discovered[ep.name].append(ep)
        except Exception:
            pass
    return discovered


def list_plugins() -> list[dict[str, str]]:
    """Flat list of all discovered plugins."""
    plugins: list[dict[str, str]] = []
    for kind, eps in discover_plugins().items():
        for ep in eps:
            plugins.append({
                "type": kind,
                "name": ep.value,
                "package": ep.module,
                "version": getattr(ep, "version", ""),
            })
    return plugins
