"""Test data lifecycle management — version, track, expire, and clean up test data.

Supports:
- Data versioning (hash-based, git-like snapshots)
- TTL-based expiry
- Reference counting (multiple tests sharing same dataset)
- Cleanup policies (age-based, count-based, manual)
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class DataVersion:
    """A single versioned snapshot of test data."""
    version_id: str         # SHA-256 of content
    created_at: float       # unix timestamp
    size_bytes: int
    source: str             # path or URL
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class DataReference:
    """A reference from a test to a dataset."""
    data_id: str            # version_id of the data
    test_id: str            # test that uses this data
    pinned: bool = False    # if pinned, never auto-expire


class DataLifecycleManager:
    """Manage test data versions, references, and cleanup."""

    def __init__(self, store_dir: str = "workspace/test-data",
                 default_ttl_days: int = 30, max_versions: int = 100) -> None:
        self._store = Path(store_dir)
        self._store.mkdir(parents=True, exist_ok=True)
        self._ttl = default_ttl_days
        self._max_versions = max_versions
        self._index: dict[str, DataVersion] = {}        # version_id → version
        self._refs: dict[str, list[DataReference]] = defaultdict(list)  # version_id → refs
        self._load_index()

    # ── index persistence ──

    def _index_path(self) -> Path:
        return self._store / ".lifecycle_index.json"

    def _load_index(self) -> None:
        ip = self._index_path()
        if ip.exists():
            data = json.loads(ip.read_text(encoding="utf-8"))
            for vid, v in data.get("versions", {}).items():
                self._index[vid] = DataVersion(**v)
            for vid, refs in data.get("refs", {}).items():
                self._refs[vid] = [DataReference(**r) for r in refs]

    def _save_index(self) -> None:
        data = {
            "versions": {vid: {
                "version_id": v.version_id,
                "created_at": v.created_at,
                "size_bytes": v.size_bytes,
                "source": v.source,
                "tags": v.tags,
                "metadata": v.metadata,
            } for vid, v in self._index.items()},
            "refs": {vid: [{
                "data_id": r.data_id,
                "test_id": r.test_id,
                "pinned": r.pinned,
            } for r in refs] for vid, refs in self._refs.items()},
        }
        self._index_path().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── CRUD ──

    def put(self, content: str | bytes, source: str = "",
            tags: list[str] | None = None,
            metadata: dict[str, str] | None = None) -> str:
        """Store test data and return version_id."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        version_id = hashlib.sha256(content).hexdigest()[:16]

        if version_id in self._index:
            return version_id  # Dedup

        # Write content
        data_file = self._store / f"{version_id}.json"
        data_file.write_bytes(content)

        v = DataVersion(
            version_id=version_id,
            created_at=time.time(),
            size_bytes=len(content),
            source=source,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._index[version_id] = v
        self._save_index()
        return version_id

    def get(self, version_id: str) -> str | None:
        """Get test data content by version_id."""
        if version_id not in self._index:
            return None
        data_file = self._store / f"{version_id}.json"
        if not data_file.exists():
            del self._index[version_id]
            self._save_index()
            return None
        return data_file.read_text(encoding="utf-8")

    def ref(self, data_id: str, test_id: str, pinned: bool = False) -> None:
        """Add a reference from a test to a dataset."""
        if data_id not in self._index:
            raise KeyError(f"data '{data_id}' not found")
        self._refs[data_id].append(DataReference(
            data_id=data_id, test_id=test_id, pinned=pinned,
        ))
        self._save_index()

    def unref(self, data_id: str, test_id: str) -> None:
        """Remove a reference."""
        self._refs[data_id] = [r for r in self._refs.get(data_id, [])
                                if r.test_id != test_id]
        self._save_index()

    def list_versions(self, tag: str | None = None) -> list[DataVersion]:
        """List all data versions, optionally filtered by tag."""
        if tag:
            return [v for v in self._index.values() if tag in v.tags]
        return sorted(self._index.values(), key=lambda v: v.created_at, reverse=True)

    # ── Cleanup ──

    def expire(self, older_than_days: int | None = None) -> int:
        """Remove data versions older than threshold with zero references.
        Returns count of expired items."""
        threshold = older_than_days or self._ttl
        cutoff = time.time() - threshold * 86400
        expired_count = 0

        for vid in list(self._index):
            v = self._index[vid]
            if v.created_at < cutoff:
                refs = self._refs.get(vid, [])
                if any(r.pinned for r in refs):
                    continue  # Pinned — skip
                if len(refs) == 0:
                    self._remove_version(vid)
                    expired_count += 1

        if expired_count > 0:
            self._save_index()
        return expired_count

    def enforce_max_versions(self) -> int:
        """Enforce max version limit, removing oldest unreferenced data.
        Returns count of removed items."""
        if len(self._index) <= self._max_versions:
            return 0

        # Sort oldest first, skip referenced/pinned
        by_age = sorted(self._index.values(), key=lambda v: v.created_at)
        removed = 0
        for v in by_age:
            if len(self._index) <= self._max_versions:
                break
            refs = self._refs.get(v.version_id, [])
            if len(refs) == 0:
                self._remove_version(v.version_id)
                removed += 1

        if removed > 0:
            self._save_index()
        return removed

    def garbage_collect(self) -> dict[str, int]:
        """Full garbage collection pass: expire + enforce max + orphan cleanup.
        Returns {expired, trimmed, orphans}."""
        expired = self.expire()
        trimmed = self.enforce_max_versions()

        # Orphan cleanup: refs pointing to removed data
        orphan_count = 0
        for vid in list(self._refs):
            if vid not in self._index:
                del self._refs[vid]
                orphan_count += 1

        if orphan_count > 0:
            self._save_index()
        return {"expired": expired, "trimmed": trimmed, "orphans": orphan_count}

    def stats(self) -> dict[str, Any]:
        """Return lifecycle statistics."""
        total_bytes = sum(v.size_bytes for v in self._index.values())
        total_refs = sum(len(r) for r in self._refs.values())
        pinned = sum(1 for refs in self._refs.values() for r in refs if r.pinned)
        return {
            "total_versions": len(self._index),
            "total_bytes": total_bytes,
            "total_refs": total_refs,
            "pinned_refs": pinned,
            "store_dir": str(self._store),
        }

    def _remove_version(self, vid: str) -> None:
        """Remove a version and its data file."""
        data_file = self._store / f"{vid}.json"
        if data_file.exists():
            data_file.unlink()
        self._index.pop(vid, None)
        self._refs.pop(vid, None)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Test data lifecycle manager")
    sub = ap.add_subparsers(dest="cmd")

    put = sub.add_parser("put", help="Store test data")
    put.add_argument("file", help="File to store")

    ls = sub.add_parser("list", help="List data versions")
    ls.add_argument("--tag", default=None)

    gc = sub.add_parser("gc", help="Run garbage collection")
    gc.add_argument("--dry-run", action="store_true")

    stats = sub.add_parser("stats", help="Show lifecycle statistics")

    args = ap.parse_args()
    mgr = DataLifecycleManager()

    if args.cmd == "put":
        content = Path(args.file).read_text(encoding="utf-8")
        vid = mgr.put(content, source=args.file)
        print(f"Stored: {vid}")

    elif args.cmd == "list":
        for v in mgr.list_versions(args.tag):
            print(f"  {v.version_id}  {v.size_bytes:>8}B  {time.strftime('%Y-%m-%d %H:%M', time.localtime(v.created_at))}  {v.source}")

    elif args.cmd == "gc":
        result = mgr.garbage_collect()
        print(f"GC: {result}")

    elif args.cmd == "stats":
        s = mgr.stats()
        print(json.dumps(s, indent=2))
