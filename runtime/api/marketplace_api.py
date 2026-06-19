"""Marketplace API — browse, search, and install plugins.

Serves the marketplace web UI with data from registry.json via runtime.marketplace.catalog.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from runtime.marketplace.catalog import load_local, search as catalog_search

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

# Map registry lane to UI plugin_type
_LANE_TO_TYPE: dict[str, str] = {
    "agents": "agent",
    "skills": "skill",
    "mcp": "tool",
    "hooks": "gate",
}


def _enrich(entry) -> dict:
    """Convert a catalog Entry into the UI-friendly Plugin dict."""
    plugin_type = _LANE_TO_TYPE.get(entry.lane, entry.lane)
    return {
        "name": entry.name,
        "version": entry.version,
        "description": "",
        "author": "",
        "plugin_type": plugin_type,
        "downloads": 0,
        "rating": 0.0,
        "tags": entry.tags,
        "lane": entry.lane,
        "source_url": entry.source_url,
        "license": entry.license,
        "safety_score": entry.safety_score,
        "confidence": entry.confidence,
        "installed": entry.installed_at is not None,
    }


@router.get("/plugins")
def list_plugins(
    type: str | None = Query(None, description="Filter by plugin type (agent|skill|tool|gate)"),
    q: str | None = Query(None, description="Full-text search query"),
    sort: str = Query("stars", description="Sort order: stars|downloads|newest|name"),
    limit: int = Query(20, ge=1, le=100),
):
    """List all plugins with optional filtering, search, and sorting."""
    entries = load_local()

    # Filter by type
    if type:
        entries = [e for e in entries if _LANE_TO_TYPE.get(e.lane) == type]

    # Search
    if q:
        ql = q.lower()
        entries = [
            e
            for e in entries
            if ql in e.name.lower()
            or ql in " ".join(e.tags).lower()
            or ql in e.source_url.lower()
        ]

    # Enrich
    plugins = [_enrich(e) for e in entries]

    # Sort
    if sort == "name":
        plugins.sort(key=lambda p: p["name"].lower())
    elif sort == "newest":
        # No date field available; fall back to name
        plugins.sort(key=lambda p: p["name"].lower())
    elif sort == "downloads":
        plugins.sort(key=lambda p: p["downloads"], reverse=True)
    else:  # stars (default)
        plugins.sort(key=lambda p: p["rating"], reverse=True)

    return {"plugins": plugins[:limit], "total": len(plugins)}


@router.get("/plugins/{name}")
def plugin_detail(name: str):
    """Return detailed info for a single plugin."""
    for e in load_local():
        if e.name == name:
            return _enrich(e)
    raise HTTPException(status_code=404, detail=f"plugin '{name}' not found")


@router.get("/plugins/{name}/versions")
def plugin_versions(name: str):
    """Return available versions for a plugin (stub — registry stores single version)."""
    for e in load_local():
        if e.name == name:
            return {
                "name": name,
                "versions": [{"version": e.version, "current": True}],
            }
    raise HTTPException(status_code=404, detail=f"plugin '{name}' not found")


@router.get("/search")
def search_plugins(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
):
    """Full-text search across plugin names, tags, and URLs."""
    results = catalog_search(q, limit=limit)
    plugins = [_enrich(e) for e in results]
    return {"plugins": plugins, "total": len(plugins), "query": q}
