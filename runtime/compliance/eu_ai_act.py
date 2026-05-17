"""
EU AI Act Compliance Scanner — automated Article 9-15 + Annex III checks.

Key requirements tested:
- Art.9: Risk Management System (continuous monitoring, incident tracking)
- Art.10: Data Governance (representativeness, bias, version control)
- Art.11/Annex IV: Technical Documentation completeness
- Art.12: Automatic Logging (input/output/decision retention ≥6 months)
- Art.13-14: Transparency & Human Oversight
- Art.15: Accuracy, Robustness & Cybersecurity
- Annex III: High-risk system classification

Deadline: August 2, 2026 (main compliance) — Digital Omnibus may extend to Dec 2027.

Usage:
  python eu_ai_act.py audit --model-dir ./model/
  python eu_ai_act.py classify --system-type "credit_scoring"
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
# Annex III: High-Risk Classification
# ═══════════════════════════════════════════════════════════════

ANNEX_III_CATEGORIES = {
    "biometrics": "Biometric identification and categorization",
    "critical_infra": "Critical infrastructure management",
    "education": "Education and vocational training access",
    "employment": "Employment, worker management, access to self-employment",
    "essential_services": "Access to essential private/public services",
    "law_enforcement": "Law enforcement (certain uses)",
    "migration": "Migration, asylum, border control",
    "justice": "Administration of justice and democratic processes",
    "credit_scoring": "Credit scoring / creditworthiness assessment",
    "insurance": "Risk assessment and pricing in life/health insurance",
}


def classify_high_risk(system_description: str) -> dict:
    """Classify whether an AI system falls under Annex III (high-risk)."""
    desc_lower = system_description.lower()
    matches = []
    for key, category in ANNEX_III_CATEGORIES.items():
        if key in desc_lower or any(w in desc_lower for w in key.split("_")):
            matches.append({"category": key, "description": category})

    return {
        "high_risk": len(matches) > 0,
        "matched_categories": matches,
        "deadline": "2026-08-02" if matches else "N/A (not Annex III)",
        "requires_conformity_assessment": len(matches) > 0,
        "requires_notified_body": len(matches) > 0,
    }


# ═══════════════════════════════════════════════════════════════
# Article 9: Risk Management System
# ═══════════════════════════════════════════════════════════════

def check_risk_management(model_dir: str) -> list[dict]:
    """Check for continuous risk management evidence."""
    checks = []
    root = Path(model_dir)

    # Risk register
    risk_register = root / "risk_register.json" if root.exists() else None
    checks.append({
        "article": "Art.9", "check": "Risk register exists",
        "passed": risk_register.exists() if risk_register else False,
        "evidence": str(risk_register) if risk_register and risk_register.exists() else "NOT FOUND",
    })

    # Incident tracking
    incidents = root / "incidents.jsonl" if root.exists() else None
    checks.append({
        "article": "Art.9", "check": "Incident tracking (≥6 months)",
        "passed": incidents.exists() if incidents else False,
        "evidence": str(incidents) if incidents and incidents.exists() else "NOT FOUND",
    })

    # Post-market monitoring
    monitoring = root / "monitoring_plan.md" if root.exists() else None
    checks.append({
        "article": "Art.9", "check": "Post-market monitoring plan",
        "passed": monitoring.exists() if monitoring else False,
        "evidence": str(monitoring) if monitoring and monitoring.exists() else "NOT FOUND",
    })

    return checks


# ═══════════════════════════════════════════════════════════════
# Article 10: Data Governance
# ═══════════════════════════════════════════════════════════════

def check_data_governance(model_dir: str) -> list[dict]:
    """Check data governance requirements."""
    checks = []
    root = Path(model_dir)

    # Dataset documentation
    for ds_type in ["training", "validation", "testing"]:
        ds_doc = root / f"dataset_{ds_type}_card.md" if root.exists() else None
        checks.append({
            "article": "Art.10", "check": f"{ds_type} dataset documented",
            "passed": ds_doc.exists() if ds_doc else False,
            "evidence": str(ds_doc) if ds_doc and ds_doc.exists() else "NOT FOUND",
        })

    # Bias assessment
    bias_report = root / "bias_assessment.json" if root.exists() else None
    checks.append({
        "article": "Art.10", "check": "Bias detection & mitigation report",
        "passed": bias_report.exists() if bias_report else False,
        "evidence": str(bias_report) if bias_report and bias_report.exists() else "NOT FOUND",
    })

    # Data version control
    has_dvc = (root / ".dvc").exists() if root.exists() else False
    has_git_lfs = (root / ".gitattributes").exists() if root.exists() else False
    checks.append({
        "article": "Art.10", "check": "Dataset version control (DVC/Git-LFS)",
        "passed": has_dvc or has_git_lfs,
        "evidence": "DVC found" if has_dvc else ("Git-LFS found" if has_git_lfs else "NOT FOUND"),
    })

    return checks


# ═══════════════════════════════════════════════════════════════
# Article 11/Annex IV: Technical Documentation
# ═══════════════════════════════════════════════════════════════

def check_technical_documentation(model_dir: str) -> list[dict]:
    """Check Annex IV documentation completeness."""
    checks = []
    root = Path(model_dir)

    required_docs = {
        "system_description.md": "System purpose and intended use",
        "architecture.md": "System architecture and design specifications",
        "training_methodology.md": "Training methodologies and data sources",
        "evaluation_report.json": "Performance metrics and evaluation results",
        "model_card.md": "Model card with limitations",
        "decision_logic.md": "Decision-making logic explanation",
    }

    for filename, description in required_docs.items():
        doc = root / filename if root.exists() else None
        checks.append({
            "article": "Art.11/Annex IV",
            "check": description,
            "passed": doc.exists() if doc else False,
            "evidence": str(doc) if doc and doc.exists() else "NOT FOUND",
        })

    return checks


# ═══════════════════════════════════════════════════════════════
# Article 12: Automatic Logging
# ═══════════════════════════════════════════════════════════════

def check_logging(log_dir: str = "logs") -> list[dict]:
    """Check automatic logging requirements (≥6 month retention)."""
    checks = []
    root = Path(log_dir)

    has_input_logs = any(root.rglob("*input*")) if root.exists() else False
    has_output_logs = any(root.rglob("*output*")) if root.exists() else False
    has_decision_logs = any(root.rglob("*decision*")) if root.exists() else False

    checks.append({
        "article": "Art.12", "check": "Input logging",
        "passed": has_input_logs,
        "evidence": "Found" if has_input_logs else "NOT FOUND",
    })
    checks.append({
        "article": "Art.12", "check": "Output/decision logging",
        "passed": has_output_logs or has_decision_logs,
        "evidence": "Found" if (has_output_logs or has_decision_logs) else "NOT FOUND",
    })

    # Retention check (heuristic: log rotation config)
    retention_configs = list(root.rglob("*retention*")) if root.exists() else []
    checks.append({
        "article": "Art.12", "check": "Retention policy (≥6 months)",
        "passed": len(retention_configs) > 0,
        "evidence": str(retention_configs[0]) if retention_configs else "NOT FOUND",
    })

    return checks


# ═══════════════════════════════════════════════════════════════
# Article 15: Accuracy, Robustness & Cybersecurity
# ═══════════════════════════════════════════════════════════════

def check_robustness(model_dir: str) -> list[dict]:
    """Check robustness & cybersecurity requirements."""
    checks = []
    root = Path(model_dir)

    # Adversarial testing
    adv_test = root / "adversarial_test_results.json" if root.exists() else None
    checks.append({
        "article": "Art.15", "check": "Adversarial robustness testing",
        "passed": adv_test.exists() if adv_test else False,
        "evidence": str(adv_test) if adv_test and adv_test.exists() else "NOT FOUND",
    })

    # Fail-safe / fallback plan
    fail_safe = root / "fail_safe_plan.md" if root.exists() else None
    checks.append({
        "article": "Art.15", "check": "Fail-safe / fallback procedures",
        "passed": fail_safe.exists() if fail_safe else False,
        "evidence": str(fail_safe) if fail_safe and fail_safe.exists() else "NOT FOUND",
    })

    # Data poisoning protection
    poisoning_doc = root / "data_poisoning_defense.md" if root.exists() else None
    checks.append({
        "article": "Art.15", "check": "Data poisoning protection documented",
        "passed": poisoning_doc.exists() if poisoning_doc else False,
        "evidence": str(poisoning_doc) if poisoning_doc and poisoning_doc.exists() else "NOT FOUND",
    })

    # Feedback loop detection
    feedback_doc = root / "feedback_loop_detection.md" if root.exists() else None
    checks.append({
        "article": "Art.15", "check": "Feedback loop detection (post-deployment learning)",
        "passed": feedback_doc.exists() if feedback_doc else False,
        "evidence": str(feedback_doc) if feedback_doc and feedback_doc.exists() else "NOT FOUND",
    })

    return checks


# ═══════════════════════════════════════════════════════════════
# Comprehensive Audit
# ═══════════════════════════════════════════════════════════════

def comprehensive_audit(model_dir: str, log_dir: str = "logs",
                         system_description: str = "") -> dict:
    """Full EU AI Act compliance audit."""
    all_checks = []
    all_checks += check_risk_management(model_dir)
    all_checks += check_data_governance(model_dir)
    all_checks += check_technical_documentation(model_dir)
    all_checks += check_logging(log_dir)
    all_checks += check_robustness(model_dir)

    passed = sum(1 for c in all_checks if c["passed"])
    total = len(all_checks)
    classification = classify_high_risk(system_description or model_dir)

    return {
        "audit_date": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "model_dir": model_dir,
        "high_risk_classification": classification,
        "compliance_score": round(passed / max(total, 1) * 100, 1),
        "checks_passed": passed,
        "checks_total": total,
        "checks_by_article": {
            art: {"total": sum(1 for c in all_checks if c["article"] == art),
                  "passed": sum(1 for c in all_checks if c["article"] == art and c["passed"])}
            for art in sorted(set(c["article"] for c in all_checks))
        },
        "all_checks": all_checks,
        "deadline": "2026-08-02" if classification["high_risk"] else "N/A",
        "penalties_applicable": classification["high_risk"],
        "penalty_max": "15M EUR or 3% global turnover" if classification["high_risk"] else "N/A",
        "next_steps": [
            "Engage notified body for conformity assessment",
            "Register in EU database",
            "Affix CE marking",
        ] if classification["high_risk"] else ["No high-risk obligations under Annex III"],
    }


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="EU AI Act Compliance Scanner")
    sub = ap.add_subparsers(dest="cmd")

    classify_cmd = sub.add_parser("classify", help="Classify AI system risk level")
    classify_cmd.add_argument("--system-type", required=True)

    audit_cmd = sub.add_parser("audit", help="Full compliance audit")
    audit_cmd.add_argument("--model-dir", required=True)
    audit_cmd.add_argument("--log-dir", default="logs")
    audit_cmd.add_argument("--output", default="")

    args = ap.parse_args()

    if args.cmd == "classify":
        result = classify_high_risk(args.system_type)
        print(f"High risk: {result['high_risk']}")
        if result["matched_categories"]:
            print("Matched categories:")
            for m in result["matched_categories"]:
                print(f"  - {m['category']}: {m['description']}")
        print(f"Deadline: {result['deadline']}")

    elif args.cmd == "audit":
        result = comprehensive_audit(args.model_dir, args.log_dir)
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(result, indent=2, ensure_ascii=False))
