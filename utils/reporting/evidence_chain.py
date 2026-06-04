# SPDX-License-Identifier: MIT
"""
证据链可采信性打包器 - 司法/审计/监管送审

构建不可篡改的证据保管链:
- 多源证据收集 (decisions / DORA / tracing / baselines / history)
- SHA-256 哈希链确保完整性 (chain of custody)
- 合规标准映射 (ISO 27001 / SOC 2 / NIST 800-53 / GDPR)
- JSON 标准送审包 + Markdown 保管链报告

被引用方: bug-manager / test-lead / 合规审计场景
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from paths import get_output_dir, current_run_id

logger = logging.getLogger(__name__)

# ── Compliance standards reference ──

COMPLIANCE_STANDARDS: dict[str, dict[str, str]] = {
    "ISO_27001": {
        "A.12.4": "Logging and monitoring",
        "A.12.7": "Information systems audit considerations",
        "A.14.2.5": "Secure system engineering principles",
        "A.16.1.5": "Response to information security incidents",
        "A.18.1.4": "Privacy and protection of PII",
    },
    "SOC2": {
        "CC7.2": "System monitoring and alerts",
        "CC7.3": "Incident detection and response",
        "CC7.4": "Incident response and remediation",
        "CC8.2": "Change management",
    },
    "NIST_800_53": {
        "AU-3": "Content of audit records",
        "AU-6": "Audit review, analysis, and reporting",
        "AU-11": "Audit record retention",
        "CM-3": "Configuration change control",
        "IR-5": "Incident monitoring",
    },
    "GDPR": {
        "Art_30": "Records of processing activities",
        "Art_32": "Security of processing",
        "Art_33": "Notification of personal data breach",
    },
}


# ── Data classes ──

@dataclass
class EvidenceItem:
    """Single piece of evidence with hash chain link."""
    id: str
    source: str
    category: str
    timestamp: str
    content: dict[str, Any]
    content_hash: str = ""
    previous_hash: str | None = None

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hash_content(self.content)


@dataclass
class ChainOfCustody:
    """Immutable chain of custody linking evidence items via hash."""
    chain_id: str
    items: list[EvidenceItem] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def root_hash(self) -> str:
        if not self.items:
            return hashlib.sha256(b"").hexdigest()
        combined = "".join(item.content_hash for item in self.items)
        return hashlib.sha256(combined.encode()).hexdigest()

    def add(self, item: EvidenceItem) -> "ChainOfCustody":
        if self.items:
            item.previous_hash = self.items[-1].content_hash
        self.items.append(item)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return self


@dataclass
class EvidencePackage:
    """Complete evidence package for submission."""
    package_id: str
    chain: ChainOfCustody
    metadata: dict[str, Any] = field(default_factory=dict)
    compliance: dict[str, list[str]] = field(default_factory=dict)
    integrity_proof: str = ""
    exported_at: str = ""

    def seal(self) -> "EvidencePackage":
        self.integrity_proof = self.chain.root_hash()
        self.exported_at = datetime.now(timezone.utc).isoformat()
        return self


# ── Hashing ──

def hash_content(content: Any) -> str:
    """SHA-256 of JSON-serialized content (sorted keys = deterministic)."""
    raw = json.dumps(content, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── Collectors ──

def collect_decisions(decisions_dir: Path) -> list[dict[str, Any]]:
    """Collect decision logs from workspace decisions directory."""
    items: list[dict[str, Any]] = []
    if not decisions_dir.exists():
        logger.warning("Decisions directory not found: %s", decisions_dir)
        return items
    for f in sorted(decisions_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            items.append({
                "file": f.name,
                "timestamp": data.get("ts", data.get("timestamp", "")),
                "verdict": data.get("verdict", ""),
                "rationale": data.get("rationale", ""),
                "metrics": data.get("metrics", {}),
                "risks": data.get("known_risks", []),
            })
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Skipping unparseable decision %s: %s", f.name, e)
    return items


def collect_dora_metrics(deployments: list[dict[str, Any]],
                         incidents: list[dict[str, Any]],
                         git_dir: str = ".") -> dict[str, Any]:
    """Collect DORA 4 metrics snapshot from deployment/incident data."""
    try:
        from dora_metrics import dora_summary  # type: ignore[import-untyped]
        return dora_summary(deployments, incidents, git_dir)
    except ImportError:
        logger.warning("dora_metrics module not available")
        return {"error": "dora_metrics unavailable",
                "deployments": len(deployments), "incidents": len(incidents)}


def collect_tracing_validation(trace_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate tracing validation results."""
    if not trace_results:
        return {"traces_checked": 0, "passed": 0, "pass_rate": None, "services": []}
    passed = sum(1 for t in trace_results if t.get("pass"))
    all_services: list[str] = []
    for t in trace_results:
        all_services.extend(t.get("services_found", []))
    return {
        "traces_checked": len(trace_results),
        "passed": passed,
        "pass_rate": round(passed / len(trace_results), 3),
        "services": sorted(set(all_services)),
    }


def collect_baselines(baseline_path: Path | None = None) -> dict[str, Any]:
    """Collect performance baseline data."""
    if baseline_path is None:
        baseline_path = get_output_dir("baselines") / "perf_baseline.json"
    if not baseline_path.exists():
        return {"available": False, "path": str(baseline_path)}
    try:
        return {"available": True,
                **json.loads(baseline_path.read_text(encoding="utf-8"))}
    except (json.JSONDecodeError, OSError) as e:
        return {"available": False, "error": str(e)}


def collect_test_history(history_dir: Path | None = None) -> list[dict[str, Any]]:
    """Collect recent test execution history metadata."""
    if history_dir is None:
        history_dir = get_output_dir("history")
    items: list[dict[str, Any]] = []
    if not history_dir.exists():
        return items
    for f in sorted(history_dir.glob("*.xml"))[:50]:
        items.append({
            "file": f.name,
            "size": f.stat().st_size,
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return items


# ── Chain builder ──

def _map_compliance(chain: ChainOfCustody) -> dict[str, list[str]]:
    """Map evidence sources to applicable compliance controls."""
    mapping: dict[str, list[str]] = {}
    sources = {item.source for item in chain.items}

    if "decisions" in sources:
        mapping["ISO_27001"] = ["A.12.4", "A.12.7", "A.16.1.5"]
        mapping["SOC2"] = ["CC7.3", "CC7.4"]
        mapping["NIST_800_53"] = ["AU-3", "AU-6"]

    if "dora_metrics" in sources:
        mapping.setdefault("SOC2", []).extend(["CC8.2"])
        mapping.setdefault("NIST_800_53", []).extend(["CM-3"])

    if "test_history" in sources:
        mapping.setdefault("ISO_27001", []).extend(["A.14.2.5"])
        mapping.setdefault("NIST_800_53", []).extend(["AU-11"])

    if "tracing_validator" in sources:
        mapping.setdefault("SOC2", []).extend(["CC7.2"])
        mapping.setdefault("NIST_800_53", []).extend(["AU-6", "IR-5"])

    return mapping


def build_evidence_chain(
    decisions_dir: Path | None = None,
    dora_deployments: list[dict[str, Any]] | None = None,
    dora_incidents: list[dict[str, Any]] | None = None,
    trace_results: list[dict[str, Any]] | None = None,
    baseline_path: Path | None = None,
    history_dir: Path | None = None,
    package_metadata: dict[str, Any] | None = None,
) -> EvidencePackage:
    """Build complete evidence chain from all available sources."""
    now = datetime.now(timezone.utc)
    chain = ChainOfCustody(
        chain_id=f"evidence-{now.strftime('%Y%m%dT%H%M%SZ')}",
        created_at=now.isoformat(),
    )

    # 1. Decision logs
    dec_dir = decisions_dir or get_output_dir("decisions")
    decisions = collect_decisions(dec_dir)
    if decisions:
        chain.add(EvidenceItem(
            id=f"decisions-{now.strftime('%Y%m%dT%H%M%SZ')}",
            source="decisions",
            category="decision_log",
            timestamp=now.isoformat(),
            content={"count": len(decisions), "items": decisions},
        ))

    # 2. DORA metrics
    if dora_deployments:
        dora = collect_dora_metrics(dora_deployments, dora_incidents or [])
        chain.add(EvidenceItem(
            id=f"dora-{now.strftime('%Y%m%dT%H%M%SZ')}",
            source="dora_metrics",
            category="devops_metrics",
            timestamp=now.isoformat(),
            content=dora,
        ))

    # 3. Tracing validation
    if trace_results:
        tracing = collect_tracing_validation(trace_results)
        chain.add(EvidenceItem(
            id=f"tracing-{now.strftime('%Y%m%dT%H%M%SZ')}",
            source="tracing_validator",
            category="trace_validation",
            timestamp=now.isoformat(),
            content=tracing,
        ))

    # 4. Performance baselines
    bl = collect_baselines(baseline_path)
    if bl.get("available"):
        chain.add(EvidenceItem(
            id=f"baselines-{now.strftime('%Y%m%dT%H%M%SZ')}",
            source="perf_baselines",
            category="performance_baseline",
            timestamp=now.isoformat(),
            content=bl,
        ))

    # 5. Test execution history
    history = collect_test_history(history_dir)
    if history:
        chain.add(EvidenceItem(
            id=f"history-{now.strftime('%Y%m%dT%H%M%SZ')}",
            source="test_history",
            category="test_execution",
            timestamp=now.isoformat(),
            content={"files": len(history), "items": history},
        ))

    compliance = _map_compliance(chain)

    from pathlib import Path as _EPath
    _ev = _EPath(__file__).resolve().parents[2] / "VERSION"
    _ev_ver = _ev.read_text(encoding="utf-8").strip() if _ev.is_file() else "1.0.0"
    pkg = EvidencePackage(
        package_id=f"EP-{now.strftime('%Y%m%d-%H%M%S')}",
        chain=chain,
        metadata=package_metadata or {
            "generator": "evidence_chain.py",
            "version": _ev_ver,
            "generated_by": os.environ.get("USER",
                                            os.environ.get("USERNAME", "unknown")),
        },
        compliance=compliance,
    )
    pkg.seal()
    return pkg


# ── Verification ──

def verify_chain_integrity(package: EvidencePackage) -> dict[str, Any]:
    """Verify evidence chain integrity. Recomputes all hashes and checks links."""
    results: dict[str, Any] = {"pass": True, "checks": [], "tampered": []}
    chain = package.chain

    for i, item in enumerate(chain.items):
        recomputed = hash_content(item.content)
        if recomputed != item.content_hash:
            results["pass"] = False
            results["tampered"].append({
                "index": i, "id": item.id, "reason": "content_hash mismatch",
            })
            results["checks"].append(
                {"index": i, "check": "content_hash", "pass": False})
        else:
            results["checks"].append(
                {"index": i, "check": "content_hash", "pass": True})

    for i in range(1, len(chain.items)):
        expected = chain.items[i - 1].content_hash
        actual = chain.items[i].previous_hash
        if actual != expected:
            results["pass"] = False
            results["tampered"].append({
                "index": i, "id": chain.items[i].id,
                "reason": "broken chain link",
            })

    recomputed_root = chain.root_hash()
    if recomputed_root != package.integrity_proof:
        results["pass"] = False
        results["tampered"].append({"reason": "integrity_proof mismatch"})

    results["total_items"] = len(chain.items)
    results["root_hash"] = recomputed_root
    return results


# ── Export ──

def export_package(package: EvidencePackage,
                   output_path: Path | None = None) -> str:
    """Export evidence package as JSON file."""
    if output_path is None:
        output_path = Path(
            str(get_output_dir("evidence", current_run_id()) / f"{package.package_id}.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    serialized: dict[str, Any] = {
        "package_id": package.package_id,
        "metadata": package.metadata,
        "compliance": package.compliance,
        "integrity_proof": package.integrity_proof,
        "exported_at": package.exported_at,
        "chain": {
            "chain_id": package.chain.chain_id,
            "created_at": package.chain.created_at,
            "updated_at": package.chain.updated_at,
            "root_hash": package.chain.root_hash(),
            "item_count": len(package.chain.items),
            "items": [
                {
                    "id": item.id,
                    "source": item.source,
                    "category": item.category,
                    "timestamp": item.timestamp,
                    "content_hash": item.content_hash,
                    "previous_hash": item.previous_hash,
                    "content": item.content,
                }
                for item in package.chain.items
            ],
        },
    }

    output_path.write_text(
        json.dumps(serialized, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    logger.info("Evidence package exported: %s", output_path)
    return str(output_path)


def export_chain_of_custody_report(
    package: EvidencePackage, output_path: Path | None = None
) -> str:
    """Export human-readable chain of custody report as Markdown."""
    if output_path is None:
        output_path = Path(
            str(get_output_dir("evidence", current_run_id()) / f"{package.package_id}_custody.md"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Chain of Custody Report",
        "",
        f"**Package ID**: `{package.package_id}`",
        f"**Chain ID**: `{package.chain.chain_id}`",
        f"**Created**: {package.chain.created_at}",
        f"**Integrity Proof**: `{package.integrity_proof[:16]}...`",
        f"**Items**: {len(package.chain.items)}",
        "",
        "## Evidence Items",
        "",
    ]

    for item in package.chain.items:
        lines.append(f"### {item.id}")
        lines.append(f"- **Source**: {item.source}")
        lines.append(f"- **Category**: {item.category}")
        lines.append(f"- **Timestamp**: {item.timestamp}")
        lines.append(f"- **Hash**: `{item.content_hash[:16]}...`")
        if item.previous_hash:
            lines.append(f"- **Previous**: `{item.previous_hash[:16]}...`")
        lines.append("")

    lines.append("## Compliance Coverage")
    for std, controls in package.compliance.items():
        lines.append(f"- **{std}**: {', '.join(controls)}")

    lines.append("")
    lines.append("---")
    lines.append(f"*Report generated {package.exported_at}*")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return str(output_path)


# ── Compliance ──

def compliance_matrix() -> dict[str, dict[str, str]]:
    """Return full compliance standards reference."""
    return dict(COMPLIANCE_STANDARDS)


# ── CI summary ──

def ci_summary(package: EvidencePackage) -> dict[str, Any]:
    """CI-friendly one-line summary of evidence package."""
    verification = verify_chain_integrity(package)
    return {
        "package_id": package.package_id,
        "items": len(package.chain.items),
        "sources": sorted(set(item.source for item in package.chain.items)),
        "root_hash": package.chain.root_hash()[:16],
        "integrity_verified": verification["pass"],
        "compliance_standards": sorted(package.compliance.keys()),
        "decision_count": sum(
            1 for item in package.chain.items if item.source == "decisions"),
        "dora_available": any(
            item.source == "dora_metrics" for item in package.chain.items),
        "tampered": len(verification["tampered"]),
    }


# ── Convenience ──

def quick_package(workspace_dir: Path | None = None) -> EvidencePackage:
    """Build evidence package from default workspace paths."""
    if workspace_dir is None:
        return build_evidence_chain(
            decisions_dir=get_output_dir("decisions"),
            baseline_path=get_output_dir("baselines") / "perf_baseline.json",
            history_dir=get_output_dir("history"),
        )
    return build_evidence_chain(
        decisions_dir=workspace_dir / "测试报告/decisions/",
        baseline_path=workspace_dir / "测试报告/baselines/perf_baseline.json",
        history_dir=workspace_dir / "测试报告/history/",
    )
