"""Expert + Skill registry.

Scans `agents/*.md` and `skills/*.md`, parses YAML frontmatter,
exposes a unified catalog for router/orchestrator/api.

Frontmatter contract (already present in existing files):

    ---
    name: <id>
    description: <one-liner>
    tools: <comma-list, optional>
    ---
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from loguru import logger

from runtime.config.settings import get_settings

EntryKind = Literal["expert", "skill"]

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)

# 合法 impl_status (与 agents/*.md / skills/*.md frontmatter 严同步)
_VALID_IMPL_STATUS = {"production", "script", "rollout", "vision"}


@dataclass(slots=True)
class CatalogEntry:
    kind: EntryKind
    name: str
    description: str
    tools: list[str] = field(default_factory=list)
    source_path: str = ""
    raw_body: str = ""
    # 防 mock:
    # 从 frontmatter EXPERT_IMPL_STATUS / SKILL_IMPL_STATUS 解析,执行层据此拒绝路由未实装项。
    # 合法值: production / script / rollout / vision / unknown(frontmatter 缺失或值非法时)。
    impl_status: str = "unknown"

    def short(self) -> dict:
        return {
            "kind": self.kind,
            "name": self.name,
            "description": self.description,
            "impl_status": self.impl_status,
        }


@dataclass(slots=True)
class Catalog:
    experts: dict[str, CatalogEntry] = field(default_factory=dict)
    skills: dict[str, CatalogEntry] = field(default_factory=dict)

    def all(self) -> list[CatalogEntry]:
        return list(self.experts.values()) + list(self.skills.values())

    def lookup(self, name: str) -> CatalogEntry | None:
        return self.experts.get(name) or self.skills.get(name)

    def to_dict(self) -> dict:
        return {
            "experts": [e.short() for e in self.experts.values()],
            "skills": [s.short() for s in self.skills.values()],
        }

    def to_full_dict(self) -> dict:
        return {
            "experts": [asdict(e) for e in self.experts.values()],
            "skills": [asdict(s) for s in self.skills.values()],
        }


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        logger.warning("frontmatter parse failed: {}", e)
        meta = {}
    return meta, m.group(2)


def _entry_from_file(path: Path, kind: EntryKind) -> CatalogEntry | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        logger.warning("read failed {}: {}", path, e)
        return None
    meta, body = _parse_frontmatter(text)
    name = meta.get("name")
    description = meta.get("description", "")
    if not name:
        has_fm = text.startswith("---")
        if has_fm:
            logger.warning("skip {} — frontmatter missing 'name' field (YAML may be broken)", path)
        else:
            logger.debug("skip {} (no frontmatter)", path)
        return None
    tools_raw = meta.get("tools", "")
    if isinstance(tools_raw, list):
        tools = [str(t).strip() for t in tools_raw if str(t).strip()]
    elif isinstance(tools_raw, str):
        tools = [t.strip() for t in tools_raw.split(",") if t.strip()]
    else:
        tools = []
    # 防 mock: 按 kind 选对应 frontmatter key,缺失或非法值降级 unknown
    status_key = "EXPERT_IMPL_STATUS" if kind == "expert" else "SKILL_IMPL_STATUS"
    status_raw = meta.get(status_key, "")
    impl_status = str(status_raw).strip().lower() if status_raw else ""
    if impl_status not in _VALID_IMPL_STATUS:
        if impl_status:
            logger.debug("{} {} {}={!r} 非法,降级 unknown", kind, name, status_key, status_raw)
        impl_status = "unknown"
    return CatalogEntry(
        kind=kind,
        name=str(name),
        description=str(description),
        tools=tools,
        source_path=str(path),
        raw_body=body,
        impl_status=impl_status,
    )


def build_catalog() -> Catalog:
    s = get_settings()
    experts_dir = s.resolve(s.experts_dir)
    skills_dir = s.resolve(s.skills_dir)
    cat = Catalog()
    for md in sorted(experts_dir.glob("*.md")):
        if md.name.upper() in {"README.MD", "INDEX.MD"}:
            continue
        e = _entry_from_file(md, "expert")
        if e:
            cat.experts[e.name] = e
    for md in sorted(skills_dir.glob("*.md")):
        if md.name.upper() in {"README.MD", "INDEX.MD"}:
            continue
        e = _entry_from_file(md, "skill")
        if e:
            cat.skills[e.name] = e
    logger.info("catalog built: {} experts, {} skills", len(cat.experts), len(cat.skills))
    return cat


def dump_catalog(target: Path | None = None) -> Path:
    get_settings()
    target = target or (Path(__file__).parent / "catalog.json")
    cat = build_catalog()
    target.write_text(
        json.dumps(cat.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("catalog dumped -> {}", target)
    return target


_cache: Catalog | None = None


def get_catalog(refresh: bool = False) -> Catalog:
    global _cache
    if refresh or _cache is None:
        _cache = build_catalog()
    return _cache
