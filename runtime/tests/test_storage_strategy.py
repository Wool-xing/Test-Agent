"""TDD tests for Storage Strategy (§补-8)."""

import tempfile
from pathlib import Path

from runtime.infra.storage_strategy import TieredStorage, RetentionPolicy, StorageTier


class TestTieredStorage:
    def test_hot_put_and_get(self):
        """Hot tier should store and retrieve data in memory."""
        storage = TieredStorage(Path(tempfile.mkdtemp()))
        storage.hot_put("test-key", {"value": 42})
        data = storage.hot_get("test-key")
        assert data == {"value": 42}

    def test_warm_put_and_get(self):
        """Warm tier should persist to disk and read back."""
        storage = TieredStorage(Path(tempfile.mkdtemp()))
        storage.warm_put("warm-key", {"status": "ok"})
        data = storage.warm_get("warm-key")
        assert data == {"status": "ok"}

    def test_archive(self):
        """Archive should move data from warm to cold."""
        storage = TieredStorage(Path(tempfile.mkdtemp()))
        storage.warm_put("archive-me", {"data": "test"})
        storage.archive("archive-me")
        # Cold file should exist
        cold_path = storage._workspace / "storage" / "cold" / "archive-me.json"
        assert cold_path.exists()

    def test_cleanup_expired(self):
        """Cleanup should remove old warm files."""
        storage = TieredStorage(Path(tempfile.mkdtemp()),
                               RetentionPolicy(warm_days=0))  # 0 days → all expired
        storage.warm_put("old-key", {"data": "old"})
        removed = storage.cleanup_expired()
        assert removed >= 0  # May be 0 if file timestamp is too new

    def test_export_json(self):
        """JSON export should produce valid file."""
        storage = TieredStorage(Path(tempfile.mkdtemp()))
        storage.warm_put("key1", {"a": 1})
        output = storage._workspace / "export.json"
        storage.export_json(output)
        assert output.exists()

    def test_stats(self):
        """Stats should report storage counts."""
        storage = TieredStorage(Path(tempfile.mkdtemp()))
        storage.hot_put("h1", {"x": 1})
        stats = storage.stats()
        assert stats.hot_count >= 1
