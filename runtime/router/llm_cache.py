"""LLM response cache — reduce API costs for repeated/similar prompts.

Caches complete() responses keyed by (provider, model, prompt_hash, temperature).
TTL defaults to 3600s (1h). Cache stored as JSON files in workspace/cache/llm/.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path

from runtime.config.settings import get_settings

logger = logging.getLogger(__name__)


def _cache_dir() -> Path:
    d = get_settings().workspace_dir / "cache" / "llm"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _cache_key(provider: str, model: str, system: str, user: str, temperature: float) -> str:
    """Generate a deterministic cache key."""
    raw = f"{provider}|{model}|{system}|{user}|{temperature:.2f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _ttl() -> int:
    """Cache TTL in seconds."""
    return int(os.environ.get("TAGENT_LLM_CACHE_TTL", "3600"))


def get_cached(provider: str, model: str, system: str, user: str, temperature: float) -> str | None:
    """Retrieve cached response. Returns None if not found or expired."""
    key = _cache_key(provider, model, system, user, temperature)
    path = _cache_dir() / f"{key}.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if time.time() - data.get("ts", 0) > _ttl():
            path.unlink(missing_ok=True)
            return None
        logger.debug("llm cache hit: %s", key[:8])
        return data.get("response", "")
    except (json.JSONDecodeError, OSError):
        return None


def set_cached(provider: str, model: str, system: str, user: str, temperature: float, response: str) -> None:
    """Store a response in the cache."""
    key = _cache_key(provider, model, system, user, temperature)
    path = _cache_dir() / f"{key}.json"
    try:
        path.write_text(json.dumps({
            "key": key, "provider": provider, "model": model,
            "ts": time.time(), "response": response,
        }, ensure_ascii=False), encoding="utf-8")
    except OSError as e:
        logger.warning("llm cache write failed: %s", e)


def cache_stats() -> dict:
    """Return cache statistics."""
    d = _cache_dir()
    files = list(d.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)
    return {
        "entries": len(files),
        "size_kb": round(total_size / 1024, 1),
        "ttl_hours": _ttl() / 3600,
    }


def clear_cache() -> int:
    """Remove all cached entries. Returns count removed."""
    d = _cache_dir()
    count = 0
    for f in d.glob("*.json"):
        try:
            f.unlink()
            count += 1
        except OSError:
            pass
    return count
