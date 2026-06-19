"""Marketplace local + remote catalog.

读 marketplace/registry.json,可选拉远程 mirror,合并查询.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger

from runtime.config.settings import get_settings


@dataclass(slots=True)
class Entry:
    name: str
    version: str
    lane: str  # skills/agents/mcp/hooks
    source_url: str
    sha256: str = ""
    signature: str = ""
    license: str = ""
    safety_score: int = 0
    confidence: str = "llm-draft-unreviewed"
    source_tier: str = "low"
    installed_at: str | None = None
    tags: list[str] = field(default_factory=list)


def _registry_path() -> Path:
    s = get_settings()
    return s.project_root / "marketplace" / "registry.json"


def load_local() -> list[Entry]:
    p = _registry_path()
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.error("registry.json invalid: {}", e)
        return []
    out: list[Entry] = []
    for e in data.get("entries", []):
        url = e.get("source_url", "")
        if url and not url.startswith("https://"):
            logger.warning("marketplace entry {} has non-https source_url: {}", e.get("name", "?"), url)
        out.append(Entry(
            name=e["name"], version=e["version"], lane=e["lane"], source_url=url,
            sha256=e.get("sha256", ""), signature=e.get("signature", ""), license=e.get("license", ""),
            safety_score=int(e.get("safety_score", 0)), confidence=e.get("confidence", "llm-draft-unreviewed"),
            source_tier=e.get("source_tier", "low"), installed_at=e.get("installed_at"),
            tags=list(e.get("tags", [])),
        ))
    return out


def save_local(entries: list[Entry]) -> None:
    p = _registry_path()
    data = {
        "_comment": "Marketplace registry · 4 lane",
        "version": "1.0",
        "last_updated": "auto",
        "entries": [
            {
                "name": e.name, "version": e.version, "lane": e.lane, "source_url": e.source_url,
                "sha256": e.sha256, "signature": e.signature, "license": e.license,
                "safety_score": e.safety_score, "confidence": e.confidence,
                "source_tier": e.source_tier, "installed_at": e.installed_at, "tags": e.tags,
            }
            for e in entries
        ],
    }
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def find(name: str, lane: str | None = None) -> Entry | None:
    for e in load_local():
        if e.name == name and (lane is None or e.lane == lane):
            return e
    return None


def search(keyword: str, lane: str | None = None, limit: int = 50) -> list[Entry]:
    kw = keyword.lower()
    out: list[Entry] = []
    for e in load_local():
        if lane and e.lane != lane:
            continue
        haystack = " ".join([e.name, *e.tags, e.source_url]).lower()
        if kw in haystack:
            out.append(e)
            if len(out) >= limit:
                break
    return out
