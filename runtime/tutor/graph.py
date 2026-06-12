"""KB self-wiring graph · gbrain 派生.

零 LLM 调用:从卡片 frontmatter 的 `related_to` + `superseded_by` + body 内的 `[[wikilink]]`
抽取 typed link,建反向索引。

支持 typed edges:
  - related_to        通用关联
  - superseded_by     被替代(指向新卡)
  - extends           扩展自(指向基础卡)
  - prerequisite_of   学习前置(必须先学的卡)
  - contradicts       矛盾观点
  - tool_implements   工具实现理论(`pytest` tool implements `equivalence-partitioning`)

每条边权重默认 1.0;backlink 越多得分越高(`pagerank`-style 简化版)。
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Literal

from loguru import logger

from runtime.tutor.theory_kb import Card, get_kb

EdgeKind = Literal[
    "related_to",
    "superseded_by",
    "extends",
    "prerequisite_of",
    "contradicts",
    "tool_implements",
]

WIKILINK_RE = re.compile(r"\[\[([a-z0-9][a-z0-9\-]*)\]\]")
TYPED_LINK_RE = re.compile(r"\[\[([a-z0-9][a-z0-9\-]*)\|(\w+)\]\]")  # [[id|extends]]


@dataclass(slots=True)
class Edge:
    src: str
    dst: str
    kind: EdgeKind = "related_to"
    weight: float = 1.0


@dataclass(slots=True)
class Graph:
    edges: list[Edge] = field(default_factory=list)
    out: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))
    in_: dict[str, list[Edge]] = field(default_factory=lambda: defaultdict(list))

    def add(self, e: Edge) -> None:
        if e.src == e.dst:
            return
        self.edges.append(e)
        self.out[e.src].append(e)
        self.in_[e.dst].append(e)

    def backlinks(self, card_id: str) -> list[Edge]:
        return list(self.in_.get(card_id, []))

    def outgoing(self, card_id: str, kind: EdgeKind | None = None) -> list[Edge]:
        edges = self.out.get(card_id, [])
        return [e for e in edges if kind is None or e.kind == kind]

    def walk(self, start: str, *, depth: int = 2, kinds: tuple[EdgeKind, ...] | None = None) -> list[str]:
        """BFS walk; returns visited ids in order (deduped)."""
        seen: list[str] = [start]
        frontier = [start]
        for _ in range(depth):
            nxt: list[str] = []
            for cid in frontier:
                for e in self.out.get(cid, []):
                    if kinds is not None and e.kind not in kinds:
                        continue
                    if e.dst in seen:
                        continue
                    seen.append(e.dst)
                    nxt.append(e.dst)
            frontier = nxt
            if not frontier:
                break
        return seen

    def backlink_score(self, card_id: str) -> float:
        """Simple backlink-boosted score (more inbound = more authoritative)."""
        return float(len(self.in_.get(card_id, [])))


def _extract_edges_from_card(card: Card, body: str = "") -> Iterable[Edge]:
    # related_to → multiple related_to edges
    for dst in card.related_to:
        yield Edge(src=card.id, dst=dst, kind="related_to")
    # body wikilinks (untyped) → related_to
    for m in WIKILINK_RE.finditer(body):
        yield Edge(src=card.id, dst=m.group(1), kind="related_to")
    # body typed wikilinks [[id|kind]]
    for m in TYPED_LINK_RE.finditer(body):
        kind = m.group(2)
        if kind in ("superseded_by", "extends", "prerequisite_of", "contradicts", "tool_implements"):
            yield Edge(src=card.id, dst=m.group(1), kind=kind)  # type: ignore[arg-type]
    # superseded_by from frontmatter (defined in schema)
    # (theory_kb.Card does not currently parse this field; future extension)


def build_graph() -> Graph:
    """Build the self-wiring graph from the KB."""
    kb = get_kb()
    g = Graph()
    for card in kb.cards.values():
        body = ""
        # Card.source_path is the markdown file; read body if needed
        try:
            from pathlib import Path

            text = Path(card.source_path).read_text(encoding="utf-8")
            # strip frontmatter for body scan
            parts = text.split("---", 2)
            body = parts[2] if len(parts) >= 3 else text
        except Exception as e:
            logger.debug("knowledge graph card read skip %s: %s", card, e)
            body = ""
        for e in _extract_edges_from_card(card, body):
            g.add(e)
    logger.info("KB graph built: {} edges, {} nodes", len(g.edges), len(set([e.src for e in g.edges] + [e.dst for e in g.edges])))
    return g


_cache: Graph | None = None


def get_graph(refresh: bool = False) -> Graph:
    global _cache
    if _cache is None or refresh:
        _cache = build_graph()
    return _cache
