"""Verification Evidence (§补-14) — tamper-proof validation records.

Every "verified" claim must have evidence:
- CLI: terminal screenshot path
- TUI: screen recording/GIF path
- Web: browser screenshot + Playwright trace
- Performance: raw benchmark output
- Tests: pytest output with pass/fail counts
- Multi-platform: per-platform screenshots

Evidence stored: docs/v2.0.0/04-开发日志/evidence/round-{N}/
Naming: {round}-{feature}-{platform}-{type}.{png|gif|txt}
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class EvidenceType(Enum):
    SCREENSHOT = "png"
    RECORDING = "gif"
    LOG = "txt"
    JSON = "json"
    BENCHMARK = "bench"


@dataclass
class EvidenceRecord:
    """A single piece of verification evidence."""
    id: str
    round_num: int
    feature: str
    platform: str
    evidence_type: EvidenceType
    file_path: Path
    checksum: str = ""          # SHA-256 of evidence file
    timestamp: str = ""
    verified_by: str = ""       # Agent or human
    notes: str = ""


class EvidenceStore:
    """Manage verification evidence for /loop cycles."""

    def __init__(self, base_dir: Path | None = None):
        self._base = base_dir or Path("docs/v2.0.0/04-开发日志/evidence")
        self._records: list[EvidenceRecord] = []

    def record_round(self, round_num: int) -> Path:
        """Create a new evidence directory for a /loop round."""
        rd = self._base / f"round-{round_num}"
        rd.mkdir(parents=True, exist_ok=True)
        return rd

    def add_evidence(self, round_num: int, feature: str, platform: str,
                     etype: EvidenceType, content: str | bytes,
                     verified_by: str = "AI Agent") -> EvidenceRecord:
        """Store evidence and return record."""
        rd = self.record_round(round_num)
        filename = f"{round_num}-{feature}-{platform}-{etype.value}.{etype.value}"
        filepath = rd / filename

        if isinstance(content, str):
            data = content.encode("utf-8")
        else:
            data = content

        filepath.write_bytes(data)
        checksum = hashlib.sha256(data).hexdigest()[:16]

        rec = EvidenceRecord(
            id=f"E-{round_num}-{len(self._records)}",
            round_num=round_num, feature=feature, platform=platform,
            evidence_type=etype, file_path=filepath, checksum=checksum,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            verified_by=verified_by,
        )
        self._records.append(rec)
        return rec

    def get_evidence(self, feature: str, platform: str = "windows") -> list[EvidenceRecord]:
        """Retrieve evidence for a feature."""
        return [r for r in self._records
                if r.feature == feature and r.platform == platform]

    def verify_integrity(self, rec: EvidenceRecord) -> bool:
        """Verify evidence file hasn't been tampered with."""
        if not rec.file_path.exists():
            return False
        data = rec.file_path.read_bytes()
        current = hashlib.sha256(data).hexdigest()[:16]
        return current == rec.checksum

    def missing_evidence(self, features: list[str], platform: str = "windows") -> list[str]:
        """List features that have NO evidence."""
        with_evidence = {r.feature for r in self._records if r.platform == platform}
        return [f for f in features if f not in with_evidence]

    def summary(self) -> dict:
        """Summary of all evidence."""
        by_round = {}
        for r in self._records:
            by_round.setdefault(r.round_num, []).append(r.feature)
        return {
            "total_records": len(self._records),
            "rounds": len(by_round),
            "latest_round": max(by_round.keys()) if by_round else 0,
        }
