# SPDX-License-Identifier: MIT
"""Tests for evidence_chain.py - evidentiary chain admissibility."""
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "utils"))
from evidence_chain import (  # noqa: E402
    ChainOfCustody,
    EvidenceItem,
    EvidencePackage,
    build_evidence_chain,
    ci_summary,
    collect_baselines,
    collect_decisions,
    collect_dora_metrics,
    collect_test_history,
    collect_tracing_validation,
    compliance_matrix,
    export_chain_of_custody_report,
    export_package,
    hash_content,
    quick_package,
    verify_chain_integrity,
)

# ── Fixtures ──

@pytest.fixture
def tmp_decisions_dir():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "d1.json").write_text(json.dumps({
            "ts": "20260519T120000Z",
            "verdict": "go",
            "rationale": "All checks passed.",
            "metrics": {"pass_rate": 1.0},
        }))
        (p / "d2.json").write_text(json.dumps({
            "ts": "20260519T130000Z",
            "verdict": "conditional",
            "rationale": "上游 degraded",
            "known_risks": ["risk A"],
        }))
        (p / "bad.json").write_text("not json")
        yield p


@pytest.fixture
def sample_item():
    return EvidenceItem(
        id="ev-1",
        source="decisions",
        category="decision_log",
        timestamp="2026-05-19T12:00:00Z",
        content={"key": "value", "count": 42},
    )


@pytest.fixture
def sample_chain(sample_item):
    c = ChainOfCustody(chain_id="test-chain", created_at="2026-05-19T12:00:00Z")
    c.add(sample_item)
    return c


@pytest.fixture
def sample_package(sample_chain):
    pkg = EvidencePackage(
        package_id="EP-20260519-0001",
        chain=sample_chain,
        metadata={"generator": "test"},
    )
    pkg.seal()
    return pkg


@pytest.fixture
def sample_deployments():
    return [
        {"timestamp": "2026-05-19T10:00:00Z", "env": "prod", "success": True},
        {"timestamp": "2026-05-19T11:00:00Z", "env": "prod", "success": True},
        {"timestamp": "2026-05-19T12:00:00Z", "env": "prod", "success": False},
    ]


@pytest.fixture
def sample_incidents():
    return [
        {"started": "2026-05-19T09:00:00Z", "resolved": "2026-05-19T09:30:00Z", "severity": "P1"},
        {"started": "2026-05-19T14:00:00Z", "resolved": "2026-05-19T14:45:00Z", "severity": "P0"},
    ]


# ── Test hash_content ──

class TestHashContent:
    def test_deterministic(self):
        a = hash_content({"b": 2, "a": 1})
        b = hash_content({"a": 1, "b": 2})
        assert a == b

    def test_different_content(self):
        a = hash_content({"x": 1})
        b = hash_content({"x": 2})
        assert a != b

    def test_hex_format(self):
        h = hash_content({"test": True})
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)


# ── Test EvidenceItem ──

class TestEvidenceItem:
    def test_auto_hash(self, sample_item):
        assert len(sample_item.content_hash) == 64
        assert sample_item.previous_hash is None

    def test_explicit_hash(self):
        item = EvidenceItem(
            id="e1", source="test", category="cat",
            timestamp="2026-01-01T00:00:00Z",
            content={"x": 1}, content_hash="abc123",
        )
        assert item.content_hash == "abc123"

    def test_different_id_different_hash(self, sample_item):
        item2 = EvidenceItem(
            id="ev-2", source="decisions", category="decision_log",
            timestamp="2026-05-19T12:00:00Z", content={"key": "value", "count": 42},
        )
        assert sample_item.content_hash == item2.content_hash  # same content


# ── Test ChainOfCustody ──

class TestChainOfCustody:
    def test_empty_chain_root_hash(self):
        c = ChainOfCustody(chain_id="empty")
        assert len(c.root_hash()) == 64

    def test_add_links_previous_hash(self, sample_item):
        c = ChainOfCustody(chain_id="test")
        item2 = EvidenceItem(
            id="ev-2", source="dora", category="metrics",
            timestamp="2026-05-19T13:00:00Z", content={"mttr": 1.5},
        )
        c.add(sample_item)
        c.add(item2)
        assert item2.previous_hash == sample_item.content_hash
        assert len(c.items) == 2

    def test_root_hash_changes_after_add(self, sample_chain, sample_item):
        h1 = sample_chain.root_hash()
        item2 = EvidenceItem(
            id="ev-2", source="test", category="test",
            timestamp="now", content={"new": True},
        )
        sample_chain.add(item2)
        assert sample_chain.root_hash() != h1


# ── Test EvidencePackage ──

class TestEvidencePackage:
    def test_seal_sets_proof(self, sample_package):
        assert len(sample_package.integrity_proof) == 64
        assert sample_package.exported_at != ""

    def test_reproducible_seal(self, sample_chain):
        pkg1 = EvidencePackage(package_id="P1", chain=sample_chain)
        pkg2 = EvidencePackage(package_id="P1", chain=sample_chain)
        pkg1.seal()
        pkg2.seal()
        assert pkg1.integrity_proof == pkg2.integrity_proof


# ── Test collectors ──

class TestCollectDecisions:
    def test_collects_all_valid(self, tmp_decisions_dir):
        items = collect_decisions(tmp_decisions_dir)
        assert len(items) == 2

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            assert collect_decisions(Path(d)) == []

    def test_missing_dir(self):
        assert collect_decisions(Path("/nonexistent/path")) == []

    def test_content_fields(self, tmp_decisions_dir):
        items = collect_decisions(tmp_decisions_dir)
        assert items[0]["verdict"] == "go"
        assert items[1]["verdict"] == "conditional"


class TestCollectDoraMetrics:
    def test_returns_summary(self, sample_deployments, sample_incidents):
        result = collect_dora_metrics(sample_deployments, sample_incidents)
        assert "deployment_frequency" in result
        assert "mttr" in result

    def test_empty_deployments(self):
        result = collect_dora_metrics([], [])
        assert result["deployment_frequency"]["deployments"] == 0


class TestCollectTracingValidation:
    def test_all_pass(self):
        results = [
            {"pass": True, "services_found": ["svc-a", "svc-b"]},
            {"pass": True, "services_found": ["svc-a"]},
        ]
        r = collect_tracing_validation(results)
        assert r["pass_rate"] == 1.0

    def test_mixed(self):
        results = [{"pass": True, "services_found": ["x"]}, {"pass": False, "services_found": []}]
        r = collect_tracing_validation(results)
        assert r["pass_rate"] == 0.5

    def test_empty(self):
        r = collect_tracing_validation([])
        assert r["traces_checked"] == 0


class TestCollectBaselines:
    def test_missing_file(self):
        r = collect_baselines(Path("/nonexistent/baseline.json"))
        assert r["available"] is False

    def test_existing_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"tps": 100, "p95": 200}, f)
            path = Path(f.name)
        try:
            r = collect_baselines(path)
            assert r["available"] is True
            assert r["tps"] == 100
        finally:
            path.unlink()


class TestCollectTestHistory:
    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            assert collect_test_history(Path(d)) == []

    def test_missing_dir(self):
        assert collect_test_history(Path("/nonexistent")) == []

    def test_collects_xml(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "result1.xml").write_text("<testsuite/>")
            (p / "result2.xml").write_text("<testsuite/>")
            items = collect_test_history(p)
            assert len(items) == 2


# ── Test build_evidence_chain ──

class TestBuildEvidenceChain:
    def test_builds_from_decisions(self, tmp_decisions_dir):
        pkg = build_evidence_chain(decisions_dir=tmp_decisions_dir)
        assert len(pkg.chain.items) >= 1
        assert pkg.integrity_proof != ""

    def test_builds_from_all_sources(self, tmp_decisions_dir, sample_deployments, sample_incidents):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"tps": 50}, f)
            bp = Path(f.name)
        try:
            pkg = build_evidence_chain(
                decisions_dir=tmp_decisions_dir,
                dora_deployments=sample_deployments,
                dora_incidents=sample_incidents,
                trace_results=[{"pass": True, "services_found": ["api"]}],
                baseline_path=bp,
            )
            sources = {item.source for item in pkg.chain.items}
            assert "decisions" in sources
            assert "dora_metrics" in sources
            assert "tracing_validator" in sources
        finally:
            bp.unlink()

    def test_builds_with_nothing(self):
        pkg = build_evidence_chain(
            decisions_dir=Path("/nonexistent"),
            history_dir=Path("/nonexistent"),
        )
        assert len(pkg.chain.items) == 0
        assert len(pkg.integrity_proof) == 64


# ── Test verify_chain_integrity ──

class TestVerifyChainIntegrity:
    def test_valid_package_passes(self, sample_package):
        result = verify_chain_integrity(sample_package)
        assert result["pass"] is True
        assert result["tampered"] == []

    def test_tampered_content_fails(self, sample_package):
        sample_package.chain.items[0].content["key"] = "tampered"
        result = verify_chain_integrity(sample_package)
        assert result["pass"] is False

    def test_broken_chain_link_fails(self, sample_package, sample_item):
        item2 = EvidenceItem(
            id="ev-2", source="test", category="test",
            timestamp="now", content={"x": 1},
        )
        item2.previous_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        sample_package.chain.items.append(item2)
        sample_package.seal()
        result = verify_chain_integrity(sample_package)
        assert result["pass"] is False

    def test_wrong_integrity_proof_fails(self, sample_package):
        sample_package.integrity_proof = "bad"
        result = verify_chain_integrity(sample_package)
        assert result["pass"] is False


# ── Test exports ──

class TestExportPackage:
    def test_exports_valid_json(self, sample_package):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "test_evidence.json"
            path = export_package(sample_package, out)
            data = json.loads(Path(path).read_text())
            assert data["package_id"] == sample_package.package_id
            assert data["chain"]["item_count"] == 1

    def test_auto_path(self, sample_package, monkeypatch):
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as d:
            monkeypatch.chdir(d)
            try:
                path_str = export_package(sample_package)
                path = Path(path_str)
                assert path.exists()
                data = json.loads(path.read_text())
                assert data["package_id"] == sample_package.package_id
            finally:
                monkeypatch.chdir(str(old_cwd))


class TestExportChainOfCustodyReport:
    def test_creates_markdown(self, sample_package):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "custody.md"
            path = export_chain_of_custody_report(sample_package, out)
            content = Path(path).read_text()
            assert "# Chain of Custody Report" in content
            assert sample_package.package_id in content


# ── Test compliance ──

class TestComplianceMatrix:
    def test_returns_all_standards(self):
        m = compliance_matrix()
        assert "ISO_27001" in m
        assert "SOC2" in m
        assert "NIST_800_53" in m
        assert "GDPR" in m


# ── Test ci_summary ──

class TestCiSummary:
    def test_returns_key_fields(self, sample_package):
        s = ci_summary(sample_package)
        assert s["items"] == 1
        assert "decisions" in s["sources"]
        assert s["integrity_verified"] is True
        assert len(s["root_hash"]) == 16

    def test_with_multiple_items(self, sample_package, sample_item):
        item2 = EvidenceItem(
            id="ev-2", source="dora_metrics", category="metrics",
            timestamp="now", content={"mttr": 2.0},
        )
        sample_package.chain.add(item2)
        sample_package.seal()
        s = ci_summary(sample_package)
        assert s["items"] == 2
        assert s["dora_available"] is True


# ── Test quick_package ──

class TestQuickPackage:
    def test_returns_package(self):
        pkg = quick_package()
        assert isinstance(pkg, EvidencePackage)
        assert pkg.package_id.startswith("EP-")
        assert len(pkg.integrity_proof) == 64
