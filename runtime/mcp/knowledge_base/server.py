"""mcp-knowledge-base MCP server.

Tools:
  - embed(text): produce vector via LiteLLM
  - index_case(case_id, text): store embedding in `embeddings` table
  - index_defect(defect_id, text): same for defect
  - search_similar(text, top_k=5, source_type='case'): cosine similarity search
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from loguru import logger
from sqlalchemy import text as sql_text

from runtime.mcp.base import make_server, run_stdio, tool_decision_logged
from runtime.storage.db import get_engine, session_scope
from runtime.storage.models import Embedding

DEFAULT_EMBED_MODEL = os.getenv("TAGENT_EMBED_MODEL", "openai/text-embedding-3-small")
DEFAULT_DIM = int(os.getenv("TAGENT_EMBED_DIM", "1536"))
_EMBED_DEGRADED = False  # set True when embedding falls back to stub


def _vec_literal(vec: list[float]) -> str:
    """pgvector text literal format: '[v1,v2,...]'.
    Without registering pgvector adapter, raw lists won't bind correctly via SQLAlchemy text params.
    """
    return "[" + ",".join(f"{v:.8f}" for v in vec) + "]"


def _embed_stub(text: str, dim: int = DEFAULT_DIM) -> list[float]:
    """Deterministic stub for offline tests."""
    import hashlib
    import struct

    h = hashlib.sha256(text.encode("utf-8")).digest()
    # tile bytes into dim floats in [-1, 1]
    raw = (h * ((dim * 4 // len(h)) + 1))[: dim * 4]
    return [struct.unpack(">i", raw[i : i + 4])[0] / 0x7FFFFFFF for i in range(0, dim * 4, 4)]


async def _embed(text: str) -> list[float]:
    """Embed via LiteLLM, fallback to stub."""
    if os.getenv("TAGENT_EMBED_PROVIDER", "litellm") == "stub":
        return _embed_stub(text)
    try:
        import litellm

        resp = await litellm.aembedding(model=DEFAULT_EMBED_MODEL, input=[text])
        return resp.data[0]["embedding"]
    except Exception as e:
        global _EMBED_DEGRADED
        _EMBED_DEGRADED = True
        logger.warning("embedding failed, fallback to stub: {}", e)
        return _embed_stub(text)


@tool_decision_logged("embed")
async def tool_embed(text: str) -> dict:
    vec = await _embed(text)
    return {"dim": len(vec), "model": DEFAULT_EMBED_MODEL, "sample": vec[:8], "degraded": _EMBED_DEGRADED}


def _is_postgres() -> bool:
    """检测 backend 是否 PostgreSQL 且可达。

    L2-B 加固: db_url 配 postgres 但 psycopg/asyncpg 未装时, get_engine 调
    create_engine 会 ImportError。此处 try/except 兜底, 视为非 postgres,
    走 sqlite fallback 分支 (本文件 L83+ 已有 sqlite 分支)。

    同时检查 DB 是否可达 (短超时), 不可达则走 sqlite fallback。
    """
    try:
        eng = get_engine()
        if eng.dialect.name != "postgresql":
            return False
        # 轻量连通性检查: 用短超时尝试连接, 避免长时间阻塞
        import psycopg

        conn = psycopg.connect(
            host=eng.url.host or "localhost",
            port=eng.url.port or 5432,
            dbname=eng.url.database,
            user=eng.url.username,
            password=eng.url.password or "",
            connect_timeout=3,
        )
        conn.close()
        return True
    except Exception:
        return False


@tool_decision_logged("index_case")
async def tool_index_case(case_id: int, text: str) -> dict:
    vec = await _embed(text)
    if _is_postgres():
        with get_engine().begin() as c:
            c.execute(
                sql_text(
                    "INSERT INTO embeddings(source_type, source_id, model, dim, payload, embedding) "
                    "VALUES (:t, :i, :m, :d, :p, :e)"
                ),
                {"t": "case", "i": case_id, "m": DEFAULT_EMBED_MODEL, "d": len(vec), "p": json.dumps({"text": text[:500]}), "e": _vec_literal(vec)},
            )
        return {"indexed": True, "case_id": case_id, "dim": len(vec), "backend": "pgvector"}
    # sqlite fallback: skip vector column, store text only
    with session_scope() as s:
        e = Embedding(source_type="case", source_id=case_id, model=DEFAULT_EMBED_MODEL, dim=len(vec), payload={"text": text[:500]})
        s.add(e)
        s.flush()
        return {"indexed": True, "case_id": case_id, "dim": len(vec), "backend": "sqlite-no-vec", "embedding_id": e.id}


@tool_decision_logged("index_defect")
async def tool_index_defect(defect_id: int, text: str) -> dict:
    vec = await _embed(text)
    if _is_postgres():
        with get_engine().begin() as c:
            c.execute(
                sql_text(
                    "INSERT INTO embeddings(source_type, source_id, model, dim, payload, embedding) "
                    "VALUES (:t, :i, :m, :d, :p, :e)"
                ),
                {"t": "defect", "i": defect_id, "m": DEFAULT_EMBED_MODEL, "d": len(vec), "p": json.dumps({"text": text[:500]}), "e": _vec_literal(vec)},
            )
        return {"indexed": True, "defect_id": defect_id, "backend": "pgvector"}
    with session_scope() as s:
        e = Embedding(source_type="defect", source_id=defect_id, model=DEFAULT_EMBED_MODEL, dim=len(vec), payload={"text": text[:500]})
        s.add(e)
        s.flush()
        return {"indexed": True, "defect_id": defect_id, "backend": "sqlite-no-vec", "embedding_id": e.id}


@tool_decision_logged("search_similar")
async def tool_search_similar(text: str, top_k: int = 5, source_type: str = "case") -> dict:
    vec = await _embed(text)
    if not _is_postgres():
        return {"error": "search_similar requires Postgres + pgvector (sqlite fallback only supports indexing)"}
    try:
        with get_engine().connect() as c:
            rows = c.execute(
                sql_text(
                    "SELECT id, source_id, model, payload, 1 - (embedding <=> CAST(:v AS vector)) AS similarity "
                    "FROM embeddings WHERE source_type = :t "
                    "ORDER BY embedding <=> CAST(:v AS vector) LIMIT :k"
                ),
                {"v": _vec_literal(vec), "t": source_type, "k": top_k},
            ).mappings().all()
            return {
                "count": len(rows),
                "degraded": _EMBED_DEGRADED,
                "results": [
                    {
                        "id": r["id"],
                        "source_id": r["source_id"],
                        "similarity": float(r["similarity"]),
                        "preview": (r["payload"] or {}).get("text", "")[:200],
                    }
                    for r in rows
                ],
            }
    except Exception as e:
        logger.warning("search_similar DB error: {}", e)
        return {"error": f"search_similar unavailable: {e}"}


def build_server():
    try:
        from mcp.types import TextContent, Tool
    except ImportError as e:
        raise RuntimeError("mcp SDK not installed") from e

    server = make_server("knowledge-base")

    TOOLS = [
        Tool(
            name="embed",
            description="Embed text via LiteLLM (or stub). Returns dim + sample.",
            inputSchema={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"], "additionalProperties": False},
        ),
        Tool(
            name="index_case",
            description="Index a case row into embeddings table.",
            inputSchema={"type": "object", "properties": {"case_id": {"type": "integer"}, "text": {"type": "string"}}, "required": ["case_id", "text"], "additionalProperties": False},
        ),
        Tool(
            name="index_defect",
            description="Index a defect row into embeddings table.",
            inputSchema={"type": "object", "properties": {"defect_id": {"type": "integer"}, "text": {"type": "string"}}, "required": ["defect_id", "text"], "additionalProperties": False},
        ),
        Tool(
            name="search_similar",
            description="Cosine-similarity search over embeddings (requires Postgres+pgvector).",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5},
                    "source_type": {"type": "string", "enum": ["case", "defect", "report"], "default": "case"},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        ),
    ]

    @server.list_tools()
    async def _list_tools():
        return TOOLS

    DISPATCH = {
        "embed": tool_embed,
        "index_case": tool_index_case,
        "index_defect": tool_index_defect,
        "search_similar": tool_search_similar,
    }

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> list:
        arguments = arguments or {}
        handler = DISPATCH.get(name)
        if handler is None:
            return [TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))]
        try:
            result = await handler(**arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]
        except Exception as e:
            logger.exception("tool {} failed", name)
            return [TextContent(type="text", text=json.dumps({"error": str(e), "tool": name}))]

    return server


def main():
    server = build_server()
    asyncio.run(run_stdio(server))


if __name__ == "__main__":
    main()
