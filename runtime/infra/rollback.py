"""Deployment Rollback Strategy (§补-23).

Rollback matrix:
- CLI binary: keep .old backup, swap on rollback
- Config: auto-backup before upgrade, restore on rollback
- DB Schema: Alembic downgrade (each migration must have down script)
- Docker: stable/previous/latest tags

Rollback triggers:
- Critical smoke test failure
- Installation success rate < 95%
- 3+ reports of same CRITICAL bug
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RollbackPoint:
    """A saved state that can be rolled back to."""
    version: str
    created_at: str
    config_backup: Path | None = None
    binary_backup: Path | None = None
    db_revision: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class RollbackManager:
    """Manages rollback points for safe deployment."""

    def __init__(self, backup_dir: Path | None = None):
        self._backup_dir = backup_dir or Path("workspace/rollback")
        self._points: list[RollbackPoint] = []

    @property
    def latest(self) -> RollbackPoint | None:
        return self._points[-1] if self._points else None

    def create_point(self, version: str, config_path: Path | None = None,
                     binary_path: Path | None = None, db_revision: str = "") -> RollbackPoint:
        """Create a rollback point before upgrade."""
        import datetime
        self._backup_dir.mkdir(parents=True, exist_ok=True)

        point = RollbackPoint(
            version=version,
            created_at=datetime.datetime.now().isoformat(),
            db_revision=db_revision,
        )

        if config_path and config_path.exists():
            backup = self._backup_dir / f"config.{version}.bak"
            shutil.copy2(config_path, backup)
            point.config_backup = backup

        if binary_path and binary_path.exists():
            backup = self._backup_dir / f"binary.{version}.bak"
            shutil.copy2(binary_path, backup)
            point.binary_backup = backup

        self._points.append(point)
        return point

    def rollback(self) -> RollbackPoint | None:
        """Roll back to the most recent rollback point."""
        if not self._points:
            return None
        point = self._points.pop()
        return point

    def should_rollback(self, smoke_test_passed: bool,
                        install_success_rate: float,
                        critical_bug_count: int) -> bool:
        """Check if rollback should be triggered."""
        if not smoke_test_passed:
            return True
        if install_success_rate < 0.95:
            return True
        if critical_bug_count >= 3:
            return True
        return False

    def list_points(self) -> list[RollbackPoint]:
        return list(self._points)

    def cleanup_old(self, keep_last: int = 5) -> int:
        """Remove old rollback points, keeping the most recent N."""
        removed = 0
        while len(self._points) > keep_last:
            old = self._points.pop(0)
            for path in [old.config_backup, old.binary_backup]:
                if path and path.exists():
                    path.unlink(missing_ok=True)
            removed += 1
        return removed


# Singleton
_manager: RollbackManager | None = None


def get_rollback_manager() -> RollbackManager:
    global _manager
    if _manager is None:
        _manager = RollbackManager()
    return _manager
