# SPDX-License-Identifier: MIT
"""Knowledge Graph dashboard REST API.

Provides endpoints for exploring the graphify knowledge graph:
- /stats — graph statistics
- /community/{id} — community detail
- /path — shortest path between nodes
- /neighbors/{node_id} — neighbor lookup
- /search — node search by label
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/kg", tags=["knowledge-graph"])

DEFAULT_GRAPH_PATH = "graphify-out/graph.json"

# Module-level cache to avoid re-reading graph on every request
_graph_cache: dict | None = None


def _load_graph() -> dict:
    global _graph_cache
    if _graph_cache is not None:
        return _graph_cache
    gp = Path(DEFAULT_GRAPH_PATH)
    if not gp.exists():
        logger.warning("graph not found at %s", gp)
        _graph_cache = {}
        return _graph_cache
    with open(gp, "r", encoding="utf-8") as f:
        _graph_cache = json.load(f)
    return _graph_cache


def _graph_or_404() -> dict:
    g = _load_graph()
    if not g:
        raise HTTPException(status_code=503, detail="knowledge graph not available")
    return g


@router.get("/stats")
def kg_stats() -> dict:
    """Return graph statistics: node count, edge count, communities, top nodes by degree."""
    g = _graph_or_404()
    nodes = g.get("nodes", [])
    links = g.get("links", [])

    # Community counts
    communities = Counter(n.get("community") for n in nodes if n.get("community") is not None)

    # File type counts
    file_types = Counter(n.get("file_type", "unknown") for n in nodes)

    # Top nodes by degree
    degree: dict[str, int] = {}
    for link in links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        if src:
            degree[src] = degree.get(src, 0) + 1
        if tgt:
            degree[tgt] = degree.get(tgt, 0) + 1

    nodes_by_id = {n["id"]: n for n in nodes}
    top_nodes = sorted(
        [{"id": nid, "label": nodes_by_id.get(nid, {}).get("label", nid),
          "degree": d, "community": nodes_by_id.get(nid, {}).get("community")}
         for nid, d in degree.items()],
        key=lambda x: x["degree"], reverse=True,
    )[:20]

    return {
        "node_count": len(nodes),
        "link_count": len(links),
        "hyperedge_count": len(g.get("hyperedges", [])),
        "community_count": len(communities),
        "file_types": dict(file_types),
        "top_communities": dict(communities.most_common(10)),
        "top_nodes": top_nodes,
    }


@router.get("/community/{community_id}")
def community_detail(community_id: int) -> dict:
    """Return all nodes in a community with their connections."""
    g = _graph_or_404()
    nodes = g.get("nodes", [])
    links = g.get("links", [])

    community_nodes = [n for n in nodes if n.get("community") == community_id]
    if not community_nodes:
        raise HTTPException(status_code=404, detail=f"community {community_id} not found")

    community_ids = {n["id"] for n in community_nodes}

    # Internal links (both ends in community) vs external links (one end outside)
    internal_links = []
    external_links = []
    for link in links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        if src in community_ids and tgt in community_ids:
            internal_links.append(link)
        elif src in community_ids or tgt in community_ids:
            external_links.append(link)

    # File types in community
    file_types = Counter(n.get("file_type", "unknown") for n in community_nodes)

    return {
        "community_id": community_id,
        "node_count": len(community_nodes),
        "internal_links": len(internal_links),
        "external_links": len(external_links),
        "file_types": dict(file_types),
        "nodes": [{
            "id": n["id"],
            "label": n.get("label", ""),
            "file_type": n.get("file_type", ""),
            "source_file": n.get("source_file", ""),
        } for n in community_nodes[:200]],
    }


def _bfs_shortest_path(
    graph: dict, from_id: str, to_id: str
) -> list[str] | None:
    """BFS to find shortest path between two node IDs. Returns list of node IDs or None."""
    links = graph.get("links", [])
    adj: dict[str, set[str]] = {}
    for link in links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        if src and tgt:
            adj.setdefault(src, set()).add(tgt)
            adj.setdefault(tgt, set()).add(src)

    if from_id not in adj or to_id not in adj:
        return None

    queue = [[from_id]]
    visited = {from_id}
    while queue:
        path = queue.pop(0)
        current = path[-1]
        if current == to_id:
            return path
        for neighbor in adj.get(current, set()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])
    return None


def _resolve_node_id(query: str, graph: dict) -> str | None:
    """Resolve a fuzzy query to a node ID. Tries exact ID match, then label search."""
    nodes = graph.get("nodes", [])
    # Try exact ID match
    for n in nodes:
        if n.get("id") == query:
            return query
    # Try label match
    query_lower = query.lower()
    for n in nodes:
        if n.get("label", "").lower() == query_lower or n.get("norm_label", "") == query_lower:
            return n["id"]
    # Try partial match
    for n in nodes:
        if query_lower in n.get("norm_label", "") or query_lower in n.get("label", "").lower():
            return n["id"]
    return None


@router.get("/path")
def find_path(from_node: str = Query(...), to_node: str = Query(...)) -> dict:
    """Find shortest path between two nodes. Accepts node IDs or labels."""
    g = _graph_or_404()

    from_id = _resolve_node_id(from_node, g)
    if from_id is None:
        raise HTTPException(status_code=404, detail=f"source node not found: '{from_node}'")

    to_id = _resolve_node_id(to_node, g)
    if to_id is None:
        raise HTTPException(status_code=404, detail=f"target node not found: '{to_node}'")

    path_ids = _bfs_shortest_path(g, from_id, to_id)
    if path_ids is None:
        return {"found": False, "from": from_node, "to": to_node, "path": []}

    nodes_by_id = {n["id"]: n for n in g.get("nodes", [])}
    path_labels = []
    for nid in path_ids:
        node = nodes_by_id.get(nid, {})
        path_labels.append({
            "id": nid,
            "label": node.get("label", nid),
            "source_file": node.get("source_file", ""),
        })

    return {
        "found": True,
        "from": from_node,
        "to": to_node,
        "length": len(path_ids) - 1,
        "path": path_labels,
    }


@router.get("/neighbors/{node_id}")
def neighbors(node_id: str, depth: int = Query(1, ge=1, le=5)) -> dict:
    """Return neighbors of a node up to N hops."""
    depth = int(getattr(depth, "default", depth))
    g = _graph_or_404()

    resolved = _resolve_node_id(node_id, g)
    if resolved is None:
        raise HTTPException(status_code=404, detail=f"node not found: '{node_id}'")

    links = g.get("links", [])
    adj: dict[str, set[str]] = {}
    relations: dict[tuple[str, str], str] = {}
    for link in links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        if src and tgt:
            adj.setdefault(src, set()).add(tgt)
            adj.setdefault(tgt, set()).add(src)
            relations[(src, tgt)] = link.get("relation", "")
            relations[(tgt, src)] = link.get("relation", "")

    # BFS to given depth
    visited: dict[str, int] = {}  # node_id -> depth
    queue = [(resolved, 0)]
    nodes_by_id = {n["id"]: n for n in g.get("nodes", [])}

    while queue:
        current, d = queue.pop(0)
        if current in visited or d > depth:
            continue
        visited[current] = d
        for neighbor in adj.get(current, set()):
            if neighbor not in visited:
                queue.append((neighbor, d + 1))

    # Build result
    neighbors_list = []
    for nid, d in visited.items():
        if nid == resolved:
            continue
        node = nodes_by_id.get(nid, {})
        rel = relations.get((resolved, nid), relations.get((nid, resolved), ""))
        neighbors_list.append({
            "id": nid,
            "label": node.get("label", nid),
            "depth": d,
            "relation": rel,
            "source_file": node.get("source_file", ""),
            "community": node.get("community"),
        })

    neighbors_list.sort(key=lambda x: (x["depth"], x["label"]))
    return {
        "node_id": resolved,
        "node_label": nodes_by_id.get(resolved, {}).get("label", resolved),
        "depth": depth,
        "neighbor_count": len(neighbors_list),
        "neighbors": neighbors_list,
    }


@router.get("/search")
def search_nodes(q: str = Query(...), limit: int = Query(20, ge=1, le=100)) -> dict:
    """Search nodes by label or normalized name."""
    limit = int(getattr(limit, "default", limit))
    g = _graph_or_404()
    nodes = g.get("nodes", [])

    q_lower = q.lower()
    results = []
    for node in nodes:
        label = node.get("label", "")
        norm = node.get("norm_label", "")
        if q_lower in norm or q_lower in label.lower():
            results.append({
                "id": node["id"],
                "label": label,
                "file_type": node.get("file_type", ""),
                "source_file": node.get("source_file", ""),
                "source_location": node.get("source_location", ""),
                "community": node.get("community"),
            })
            if len(results) >= limit:
                break

    return {
        "query": q,
        "total_matches": len(results),
        "limit": limit,
        "results": results,
    }
