"""Persistence/Storage Strategy (§补-8).

Tiered storage:
  Hot (current session, running tests) → memory + WAL
  Warm (recent results, skill list) → SQLite / PostgreSQL
  Cold (archived reports) → JSON files or object storage

Data retention: default 30 days, configurable.
Data export: JSON/CSV format.
Schema migration: versioned SQL scripts.

Four data types, physically isolated:
  1. Configuration (tagent.yml, .env)
  2. Test Definitions (skills/*)
  3. Test Results (workspace/)
  4. Logs (workspace/logs/)
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class StorageTier(Enum):
    HOT = "hot"      # Memory + WAL
    WARM = "warm"    # SQLite / PostgreSQL
    COLD = "cold"    # JSON files / object storage


@dataclass
class RetentionPolicy:
    """Data retention configuration."""
    hot_days: int = 1        # Keep in-memory for 1 day
    warm_days: int = 30      # Keep in DB for 30 days
    cold_days: int = 365     # Archive for 1 year
    max_warm_records: int = 10000
    auto_cleanup: bool = True


@dataclass
class StorageStats:
    hot_count: int = 0
    warm_count: int = 0
    cold_count: int = 0
    total_size_bytes: int = 0


class TieredStorage:
    """Three-tier storage: hot (memory) → warm (DB) → cold (files)."""

    def __init__(self, workspace: Path | None = None, policy: RetentionPolicy | None = None):
        self._workspace = workspace or Path("workspace")
        self._policy = policy or RetentionPolicy()
        self._hot: dict[str, dict] = {}      # In-memory cache
        self._hot_timestamps: dict[str, float] = {}
        self._lock = threading.Lock()

    # ── Hot Tier (memory) ──────────────────────────────────

    def hot_put(self, key: str, data: dict) -> None:
        with self._lock:
            self._hot[key] = data
            self._hot_timestamps[key] = time.time()
            if len(self._hot) > self._policy.max_warm_records:
                self._evict_hot_oldest()

    def hot_get(self, key: str) -> dict | None:
        with self._lock:
            return self._hot.get(key)

    def _evict_hot_oldest(self) -> None:
        """Evict oldest hot entry. Move to warm."""
        if not self._hot_timestamps:
            return
        oldest_key = min(self._hot_timestamps, key=lambda k: self._hot_timestamps[k])
        self.warm_put(oldest_key, self._hot.pop(oldest_key))
        self._hot_timestamps.pop(oldest_key)

    # ── Warm Tier (files/DB) ───────────────────────────────

    def warm_put(self, key: str, data: dict) -> None:
        """Persist to warm storage."""
        warm_dir = self._workspace / "storage" / "warm"
        warm_dir.mkdir(parents=True, exist_ok=True)
        safe_key = key.replace("/", "_").replace("\\", "_")
        path = warm_dir / f"{safe_key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def warm_get(self, key: str) -> dict | None:
        """Read from warm storage."""
        safe_key = key.replace("/", "_").replace("\\", "_")
        path = self._workspace / "storage" / "warm" / f"{safe_key}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    # ── Cold Tier (archive) ────────────────────────────────

    def archive(self, key: str) -> None:
        """Move from warm to cold storage."""
        warm_data = self.warm_get(key)
        if warm_data is None:
            return
        cold_dir = self._workspace / "storage" / "cold"
        cold_dir.mkdir(parents=True, exist_ok=True)
        safe_key = key.replace("/", "_").replace("\\", "_")
        path = cold_dir / f"{safe_key}.json"
        path.write_text(json.dumps(warm_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Cleanup ────────────────────────────────────────────

    def cleanup_expired(self) -> int:
        """Remove expired records. Returns count removed."""
        removed = 0
        warm_dir = self._workspace / "storage" / "warm"
        if warm_dir.exists():
            cutoff = time.time() - self._policy.warm_days * 86400
            for f in warm_dir.glob("*.json"):
                if f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
        return removed

    def stats(self) -> StorageStats:
        return StorageStats(
            hot_count=len(self._hot),
            warm_count=len(list((self._workspace / "storage" / "warm").glob("*.json")))
            if (self._workspace / "storage" / "warm").exists() else 0,
        )

    # ── Export ─────────────────────────────────────────────

    def export_json(self, output_path: Path) -> None:
        """Export all warm data to a single JSON file."""
        all_data = {}
        warm_dir = self._workspace / "storage" / "warm"
        if warm_dir.exists():
            for f in warm_dir.glob("*.json"):
                key = f.stem
                all_data[key] = json.loads(f.read_text(encoding="utf-8"))
        output_path.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")

    def export_csv(self, output_path: Path, fields: list[str]) -> None:
        """Export warm data to CSV with specified fields."""
        import csv
        warm_dir = self._workspace / "storage" / "warm"
        rows = []
        if warm_dir.exists():
            for f in warm_dir.glob("*.json"):
                data = json.loads(f.read_text(encoding="utf-8"))
                rows.append({field: data.get(field, "") for field in fields})
        with open(output_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
