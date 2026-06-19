"""Theory KB loader · 反幻觉 L1.

Scans `docs/theory/**/*.{zh,en}.md`, parses frontmatter, exposes lookup API.
LLM in learn mode 只能引用 KB 中存在的 id;非 KB 输出"该领域未收录".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import yaml
from loguru import logger

from runtime.config.settings import get_settings

Lang = Literal["zh", "en"]
Confidence = Literal["high", "medium", "low", "llm-draft-unreviewed"]

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass(slots=True)
class Card:
    id: str
    category: str
    level: str
    name_zh: str
    name_en: str
    one_liner_zh: str
    one_liner_en: str
    authority: list[str] = field(default_factory=list)
    confidence: Confidence = "llm-draft-unreviewed"
    last_reviewed: str = ""
    reviewer: str = ""
    when_to_use: str = ""
    common_pitfall: str | list[str] = ""
    example: str = ""
    related_to: list[str] = field(default_factory=list)
    reading_zh: list[str] = field(default_factory=list)
    reading_en: list[str] = field(default_factory=list)
    source_path: str = ""

    def short(self, lang: Lang = "zh") -> dict:
        return {
            "id": self.id,
            "name": self.name_zh if lang == "zh" else self.name_en,
            "one_liner": self.one_liner_zh if lang == "zh" else self.one_liner_en,
            "category": self.category,
            "level": self.level,
            "confidence": self.confidence,
        }


@dataclass(slots=True)
class KB:
    cards: dict[str, Card] = field(default_factory=dict)
    by_category: dict[str, list[Card]] = field(default_factory=dict)

    def is_known_id(self, card_id: str) -> bool:
        return card_id in self.cards

    def lookup(self, card_id: str) -> Card | None:
        return self.cards.get(card_id)

    def list_categories(self) -> list[str]:
        return sorted(self.by_category)

    def list_in_category(self, category: str) -> list[Card]:
        return self.by_category.get(category, [])


def _theory_dir() -> Path:
    s = get_settings()
    return s.resolve(Path("docs/theory"))


def _parse_card(path: Path) -> Card | None:
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        logger.warning("frontmatter parse failed {}: {}", path, e)
        return None
    if not meta.get("id"):
        return None
    return Card(
        id=str(meta["id"]),
        category=str(meta.get("category", "")),
        level=str(meta.get("level", "")),
        name_zh=str(meta.get("name_zh", "")),
        name_en=str(meta.get("name_en", "")),
        one_liner_zh=str(meta.get("one_liner_zh", "")),
        one_liner_en=str(meta.get("one_liner_en", "")),
        authority=list(meta.get("authority", [])),
        confidence=str(meta.get("confidence", "llm-draft-unreviewed")),  # type: ignore[arg-type]
        last_reviewed=str(meta.get("last_reviewed", "")),
        reviewer=str(meta.get("reviewer", "")),
        when_to_use=str(meta.get("when_to_use", "")),
        common_pitfall=meta.get("common_pitfall", ""),
        example=str(meta.get("example", "")),
        related_to=list(meta.get("related_to", [])),
        reading_zh=list(meta.get("reading_zh", [])),
        reading_en=list(meta.get("reading_en", [])),
        source_path=str(path),
    )


_cache: KB | None = None


def load_kb(refresh: bool = False) -> KB:
    global _cache
    if _cache is not None and not refresh:
        return _cache
    kb = KB()
    base = _theory_dir()
    if not base.is_dir():
        logger.warning("theory dir missing: {}", base)
        _cache = kb
        return kb
    seen: set[str] = set()
    for p in sorted(base.rglob("*.md")):
        if p.name in {"INDEX.md", "_schema.yaml"}:
            continue
        card = _parse_card(p)
        if card is None:
            continue
        # zh + en 双语合并:同 id 取第一个并补字段
        if card.id in kb.cards:
            existing = kb.cards[card.id]
            # merge missing language fields
            if not existing.one_liner_en and card.one_liner_en:
                existing.one_liner_en = card.one_liner_en
            if not existing.one_liner_zh and card.one_liner_zh:
                existing.one_liner_zh = card.one_liner_zh
            existing.reading_en = list({*existing.reading_en, *card.reading_en})
            existing.reading_zh = list({*existing.reading_zh, *card.reading_zh})
        else:
            kb.cards[card.id] = card
            kb.by_category.setdefault(card.category, []).append(card)
        seen.add(card.id)
    logger.info("theory KB loaded: {} cards across {} categories", len(kb.cards), len(kb.by_category))
    _cache = kb
    return kb


def get_kb() -> KB:
    return load_kb()
