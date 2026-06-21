"""Local skill marketplace — install, search, publish to a local registry."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MarketplaceEntry:
    name: str
    version: str
    display_name: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    package_path: str = ""
    installed: bool = False


@dataclass
class MarketplaceResult:
    ok: bool
    error: str = ""
    entries: list[MarketplaceEntry] = field(default_factory=list)


def init_marketplace(workspace: Path) -> Path:
    """Initialize (or return) the local marketplace directory."""
    mp = workspace / "marketplace"
    mp.mkdir(parents=True, exist_ok=True)
    index = mp / "index.json"
    if not index.exists():
        index.write_text('{"skills": []}', encoding="utf-8")
    return mp


def _load_index(marketplace_dir: Path) -> dict:
    index_file = marketplace_dir / "index.json"
    if not index_file.exists():
        return {"skills": []}
    try:
        return json.loads(index_file.read_text(encoding="utf-8"))
    except Exception:
        return {"skills": []}


def _save_index(marketplace_dir: Path, data: dict) -> None:
    index_file = marketplace_dir / "index.json"
    index_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def publish_to_marketplace(package_path: Path, marketplace_dir: Path) -> MarketplaceResult:
    """Publish a .tar.gz skill package to the local marketplace.

    Args:
        package_path: Path to the .tar.gz skill package.
        marketplace_dir: Path to the marketplace directory.

    Returns:
        MarketplaceResult indicating success or failure.
    """
    if not package_path.exists():
        return MarketplaceResult(ok=False, error=f"Package not found: {package_path}")

    # Copy package to marketplace
    dest = marketplace_dir / package_path.name
    shutil.copy2(package_path, dest)

    # Extract metadata from index
    data = _load_index(marketplace_dir)
    skill_name = package_path.name.replace(".tar.gz", "")

    # Check for duplicate
    for entry in data["skills"]:
        if entry.get("name") == skill_name:
            return MarketplaceResult(ok=False, error=f"Skill '{skill_name}' already exists in marketplace. Use --force to overwrite.")

    data["skills"].append({
        "name": skill_name,
        "version": "1.0.0",
        "package": dest.name,
        "installed_at": str(Path.cwd()),
    })
    _save_index(marketplace_dir, data)

    return MarketplaceResult(ok=True)


def search_marketplace(keyword: str, marketplace_dir: Path) -> MarketplaceResult:
    """Search the local marketplace for skills matching a keyword.

    Args:
        keyword: Search keyword (matches name and tags).
        marketplace_dir: Path to the marketplace directory.

    Returns:
        MarketplaceResult with matching entries.
    """
    data = _load_index(marketplace_dir)
    results = []
    for entry in data.get("skills", []):
        name = entry.get("name", "")
        tags = entry.get("tags", [])
        if keyword.lower() in name.lower() or any(keyword.lower() in t.lower() for t in tags):
            results.append(MarketplaceEntry(
                name=name,
                version=entry.get("version", "?"),
                description=entry.get("description", ""),
                tags=tags,
                package_path=str(marketplace_dir / entry.get("package", "")),
                installed=Path("workspace/skills").exists() and (Path("workspace/skills") / name).is_dir(),
            ))
    return MarketplaceResult(ok=True, entries=results)


def list_marketplace(marketplace_dir: Path) -> MarketplaceResult:
    """List all skills in the local marketplace."""
    data = _load_index(marketplace_dir)
    results = []
    for entry in data.get("skills", []):
        results.append(MarketplaceEntry(
            name=entry.get("name", ""),
            version=entry.get("version", "?"),
            description=entry.get("description", ""),
            tags=entry.get("tags", []),
            package_path=str(marketplace_dir / entry.get("package", "")),
        ))
    return MarketplaceResult(ok=True, entries=results)
