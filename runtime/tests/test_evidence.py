"""TDD tests for Verification Evidence (§补-14)."""

import tempfile
from pathlib import Path

from runtime.infra.evidence import EvidenceStore, EvidenceType


class TestEvidenceStore:
    def test_record_round(self):
        """Should create round directory."""
        store = EvidenceStore(Path(tempfile.mkdtemp()))
        rd = store.record_round(1)
        assert rd.exists()
        assert "round-1" in str(rd)

    def test_add_evidence(self):
        """Should store evidence and return record."""
        store = EvidenceStore(Path(tempfile.mkdtemp()))
        rec = store.add_evidence(1, "http-check", "windows",
                                EvidenceType.LOG, "test output passed")
        assert rec.feature == "http-check"
        assert rec.file_path.exists()
        assert len(rec.checksum) > 0

    def test_get_evidence(self):
        """Should retrieve evidence by feature."""
        store = EvidenceStore(Path(tempfile.mkdtemp()))
        store.add_evidence(1, "ping-check", "windows", EvidenceType.LOG, "ok")
        store.add_evidence(1, "http-check", "windows", EvidenceType.LOG, "ok")
        results = store.get_evidence("ping-check")
        assert len(results) == 1
        assert results[0].feature == "ping-check"

    def test_missing_evidence(self):
        """Should list features without evidence."""
        store = EvidenceStore(Path(tempfile.mkdtemp()))
        store.add_evidence(1, "ping-check", "windows", EvidenceType.LOG, "ok")
        missing = store.missing_evidence(["ping-check", "http-check"])
        assert "http-check" in missing
        assert "ping-check" not in missing

    def test_verify_integrity(self):
        """Should verify evidence hasn't been tampered."""
        store = EvidenceStore(Path(tempfile.mkdtemp()))
        rec = store.add_evidence(1, "test", "windows", EvidenceType.LOG, "original")
        assert store.verify_integrity(rec) is True

    def test_summary(self):
        """Should provide evidence summary."""
        store = EvidenceStore(Path(tempfile.mkdtemp()))
        store.add_evidence(1, "test1", "windows", EvidenceType.LOG, "ok")
        store.add_evidence(1, "test2", "windows", EvidenceType.LOG, "ok")
        summary = store.summary()
        assert summary["total_records"] == 2
        assert summary["rounds"] == 1
