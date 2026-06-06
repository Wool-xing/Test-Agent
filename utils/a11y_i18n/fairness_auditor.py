# SPDX-License-Identifier: MIT
"""
Fairness & Bias Auditor — 伦理/偏见审计 (Phase 3.1).

Covers:
  - Dataset bias: representation gaps, label imbalance by sensitive attribute
  - Model fairness: demographic parity, equal opportunity, equalized odds,
    disparate impact, statistical parity difference, calibration by group
  - Decision audit: outcome distribution, intersectional analysis
  - Bias report: structured JSON with severity + remediation hints

Referenced by: 14-AI模型测试 agent + ai-test skill + 02-coverage-matrix Phase 3.
Integrates with: ai_adversarial.py (adversarial probing), suite_minimizer.py (coverage bias).

Fairness taxonomy follows IEEE 7003-2024 / NIST AI RMF 1.0 / EU AI Act Art.10.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════

@dataclass
class GroupMetrics:
    group: str
    count: int
    pos_rate: float
    accuracy: float | None = None
    tpr: float | None = None      # true positive rate (recall)
    fpr: float | None = None       # false positive rate
    precision: float | None = None
    calibration: float | None = None  # predicted_pos / actual_pos

@dataclass
class FairnessResult:
    metric: str
    value: float
    threshold: float
    passed: bool
    detail: dict[str, Any] = field(default_factory=dict)

@dataclass
class BiasReport:
    source: str                     # "dataset" | "model_predictions" | "both"
    sensitive_attributes: list[str]
    n_samples: int
    groups: list[GroupMetrics]
    fairness_results: list[FairnessResult]
    overall_severity: str            # "pass" | "warning" | "fail"
    recommendations: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# Dataset bias detection
# ═══════════════════════════════════════════════════════════════

def audit_dataset_bias(
    y_true: np.ndarray,
    sensitive: np.ndarray,
    group_names: list[str] | None = None,
    *,
    representation_threshold: float = 0.2,
    label_balance_threshold: float = 0.1,
) -> BiasReport:
    """
    Audit a dataset for representation and label bias.

    Args:
      y_true: shape (N,) binary labels (0/1 or False/True)
      sensitive: shape (N,) group membership (categorical or int-coded)
      group_names: human-readable group labels (e.g. ["male","female"])
      representation_threshold: max allowed |group_pct - 1/n_groups|
      label_balance_threshold: max allowed positive-rate gap between groups
    """
    y_true = np.asarray(y_true).ravel()
    sensitive = np.asarray(sensitive).ravel()
    unique_groups = sorted(set(sensitive))

    if group_names is None:
        group_names = [str(g) for g in unique_groups]
    if len(group_names) != len(unique_groups):
        raise ValueError("group_names length must match unique groups")

    n_total = len(y_true)
    n_groups = len(unique_groups)
    expected_pct = 1.0 / n_groups

    groups: list[GroupMetrics] = []
    fairness_results: list[FairnessResult] = []
    recommendations: list[str] = []

    max_repr_gap = 0.0
    max_label_gap = 0.0

    for g, name in zip(unique_groups, group_names):
        mask = sensitive == g
        count = int(mask.sum())
        pos_rate = float(y_true[mask].mean())
        pct = count / n_total
        gap = abs(pct - expected_pct)
        max_repr_gap = max(max_repr_gap, gap)
        groups.append(GroupMetrics(
            group=name, count=count, pos_rate=pos_rate,
        ))

    # Representation fairness
    repr_pass = max_repr_gap <= representation_threshold
    fairness_results.append(FairnessResult(
        metric="representation_parity",
        value=round(max_repr_gap, 4),
        threshold=representation_threshold,
        passed=repr_pass,
        detail={"expected_pct": round(expected_pct, 4), "per_group": {
            g.group: round(g.count / n_total, 4) for g in groups
        }},
    ))
    if not repr_pass:
        recommendations.append(
            f"Group representation imbalance detected "
            f"(max_gap={max_repr_gap:.3f} > {representation_threshold}). "
            "Consider stratified sampling or rebalancing."
        )

    # Label balance
    pos_rates = [g.pos_rate for g in groups]
    max_label_gap = max(pos_rates) - min(pos_rates)
    label_pass = max_label_gap <= label_balance_threshold
    fairness_results.append(FairnessResult(
        metric="label_balance",
        value=round(max_label_gap, 4),
        threshold=label_balance_threshold,
        passed=label_pass,
        detail={"per_group": {g.group: round(g.pos_rate, 4) for g in groups}},
    ))
    if not label_pass:
        recommendations.append(
            f"Label imbalance across groups (max_gap={max_label_gap:.3f} > "
            f"{label_balance_threshold}). Ensure labeling policy is group-agnostic."
        )

    severity = "pass"
    if not repr_pass or not label_pass:
        severity = "fail" if max_repr_gap > 2 * representation_threshold or max_label_gap > 2 * label_balance_threshold else "warning"

    return BiasReport(
        source="dataset",
        sensitive_attributes=[str(g) for g in unique_groups],
        n_samples=n_total,
        groups=groups,
        fairness_results=fairness_results,
        overall_severity=severity,
        recommendations=recommendations,
    )


# ═══════════════════════════════════════════════════════════════
# Model fairness metrics
# ═══════════════════════════════════════════════════════════════

def audit_model_fairness(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sensitive: np.ndarray,
    group_names: list[str] | None = None,
    *,
    disparate_impact_threshold: float = 0.8,
    equal_opportunity_threshold: float = 0.1,
    statistical_parity_threshold: float = 0.1,
    calibration_threshold: float = 0.1,
) -> BiasReport:
    """
    Full model fairness audit across 6 metrics.

    Args:
      y_true: ground truth labels (N,) binary
      y_pred: predicted labels (N,) binary (or soft scores ≥0.5 thresholded)
      sensitive: group membership (N,) categorical
      group_names: human-readable group names
    """
    y_true = np.asarray(y_true).ravel()
    y_pred = np.asarray(y_pred).ravel()
    sensitive = np.asarray(sensitive).ravel()
    unique_groups = sorted(set(sensitive))

    if group_names is None:
        group_names = [str(g) for g in unique_groups]

    n_total = len(y_true)
    n_groups = len(unique_groups)
    expected_pct = 1.0 / n_groups

    # Confusion matrix per group
    groups: list[GroupMetrics] = []
    for g, name in zip(unique_groups, group_names):
        mask = sensitive == g
        yt = y_true[mask]
        yp = y_pred[mask]
        count = int(mask.sum())
        tp = int(((yt == 1) & (yp == 1)).sum())
        fp = int(((yt == 0) & (yp == 1)).sum())
        tn = int(((yt == 0) & (yp == 0)).sum())
        fn = int(((yt == 1) & (yp == 0)).sum())

        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        acc = (tp + tn) / count if count > 0 else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        calib = yp.mean() / yt.mean() if yt.mean() > 0 else 1.0
        pos_rate = float(yp.mean())

        groups.append(GroupMetrics(
            group=name, count=count, pos_rate=pos_rate,
            accuracy=round(acc, 4), tpr=round(tpr, 4),
            fpr=round(fpr, 4), precision=round(prec, 4),
            calibration=round(calib, 4),
        ))

    fairness_results: list[FairnessResult] = []
    recommendations: list[str] = []

    # --- Disparate Impact (a.k.a. "80% rule") ---
    pos_rates = [g.pos_rate for g in groups]
    max_pr = max(pos_rates)
    min_pr = min(pos_rates)
    di_ratio = min_pr / max_pr if max_pr > 0 else 1.0
    di_pass = di_ratio >= disparate_impact_threshold
    fairness_results.append(FairnessResult(
        metric="disparate_impact",
        value=round(di_ratio, 4),
        threshold=disparate_impact_threshold,
        passed=di_pass,
        detail={"min_group": min(pos_rates), "max_group": max(pos_rates)},
    ))
    if not di_pass:
        recommendations.append(
            f"Disparate impact detected (ratio={di_ratio:.3f} < {disparate_impact_threshold}). "
            "Positive outcome rates differ significantly across groups."
        )

    # --- Statistical Parity Difference ---
    spd = max_pr - min_pr
    spd_pass = spd <= statistical_parity_threshold
    fairness_results.append(FairnessResult(
        metric="statistical_parity_difference",
        value=round(spd, 4),
        threshold=statistical_parity_threshold,
        passed=spd_pass,
    ))
    if not spd_pass:
        recommendations.append(
            f"Statistical parity violated (Δ={spd:.3f} > {statistical_parity_threshold})."
        )

    # --- Equal Opportunity (TPR parity) ---
    tprs = [g.tpr for g in groups if g.tpr is not None]
    if tprs:
        tpr_gap = max(tprs) - min(tprs)
        eo_pass = tpr_gap <= equal_opportunity_threshold
        fairness_results.append(FairnessResult(
            metric="equal_opportunity",
            value=round(tpr_gap, 4),
            threshold=equal_opportunity_threshold,
            passed=eo_pass,
            detail={"per_group": {g.group: g.tpr for g in groups}},
        ))
        if not eo_pass:
            recommendations.append(
                f"Equal opportunity violation (TPR gap={tpr_gap:.3f}). "
                "True positive rates differ across groups."
            )

    # --- Equalized Odds (TPR + FPR parity) ---
    fprs = [g.fpr for g in groups if g.fpr is not None]
    if tprs and fprs:
        odds_gap = max(max(tprs) - min(tprs), max(fprs) - min(fprs))
        eo_odds_pass = odds_gap <= equal_opportunity_threshold
        fairness_results.append(FairnessResult(
            metric="equalized_odds",
            value=round(odds_gap, 4),
            threshold=equal_opportunity_threshold,
            passed=eo_odds_pass,
            detail={"tpr_gap": round(max(tprs) - min(tprs), 4),
                    "fpr_gap": round(max(fprs) - min(fprs), 4)},
        ))

    # --- Calibration by group ---
    calibrations = [g.calibration for g in groups if g.calibration is not None]
    if calibrations:
        calib_gap = max(abs(c - 1.0) for c in calibrations)
        calib_pass = calib_gap <= calibration_threshold
        fairness_results.append(FairnessResult(
            metric="calibration_parity",
            value=round(calib_gap, 4),
            threshold=calibration_threshold,
            passed=calib_pass,
            detail={"per_group": {g.group: g.calibration for g in groups}},
        ))
        if not calib_pass:
            recommendations.append(
                f"Calibration gap detected ({calib_gap:.3f} > {calibration_threshold}). "
                "Predicted probabilities do not reflect true outcomes equally across groups."
            )

    # --- Predictive Parity (precision gap) ---
    precisions = [g.precision for g in groups if g.precision is not None]
    if precisions:
        prec_gap = max(precisions) - min(precisions)
        pp_pass = prec_gap <= equal_opportunity_threshold
        fairness_results.append(FairnessResult(
            metric="predictive_parity",
            value=round(prec_gap, 4),
            threshold=equal_opportunity_threshold,
            passed=pp_pass,
            detail={"per_group": {g.group: g.precision for g in groups}},
        ))

    # Overall severity
    n_failed = sum(1 for r in fairness_results if not r.passed)
    severity = "pass" if n_failed == 0 else ("fail" if n_failed >= 3 else "warning")

    return BiasReport(
        source="model_predictions",
        sensitive_attributes=[str(g) for g in unique_groups],
        n_samples=n_total,
        groups=groups,
        fairness_results=fairness_results,
        overall_severity=severity,
        recommendations=recommendations,
    )


# ═══════════════════════════════════════════════════════════════
# Intersectional fairness
# ═══════════════════════════════════════════════════════════════

def audit_intersectional(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    sensitive_attrs: dict[str, np.ndarray],
    *,
    min_group_size: int = 10,
) -> BiasReport:
    """
    Intersectional fairness audit combining multiple sensitive attributes.

    Args:
      y_true: ground truth (N,)
      y_pred: predictions (N,)
      sensitive_attrs: {"gender": array(N,), "race": array(N,), ...}
      min_group_size: ignore intersectional groups smaller than this

    Returns BiasReport with per-intersection-group metrics.
    """
    y_true = np.asarray(y_true).ravel()
    y_pred = np.asarray(y_pred).ravel()

    # Build intersectional key per sample
    attr_names = list(sensitive_attrs.keys())
    attr_arrays = [np.asarray(sensitive_attrs[k]).ravel() for k in attr_names]

    intersection_keys: list[str] = []
    group_map: dict[str, list[int]] = {}

    for i in range(len(y_true)):
        combo = "×".join(f"{k}={a[i]}" for k, a in zip(attr_names, attr_arrays))
        intersection_keys.append(combo)
        group_map.setdefault(combo, []).append(i)

    groups: list[GroupMetrics] = []
    recommendations: list[str] = []

    for combo, indices in sorted(group_map.items()):
        if len(indices) < min_group_size:
            continue
        idx_arr = np.array(indices)
        yt = y_true[idx_arr]
        yp = y_pred[idx_arr]
        count = len(indices)
        pos_rate = float(yp.mean())
        tp = int(((yt == 1) & (yp == 1)).sum())
        fp = int(((yt == 0) & (yp == 1)).sum())
        tn = int(((yt == 0) & (yp == 0)).sum())
        fn = int(((yt == 1) & (yp == 0)).sum())
        tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        acc = (tp + tn) / count if count > 0 else 0.0
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        groups.append(GroupMetrics(
            group=combo, count=count, pos_rate=pos_rate,
            accuracy=round(acc, 4), tpr=round(tpr, 4),
            fpr=round(fpr, 4), precision=round(prec, 4),
        ))

    if not groups:
        return BiasReport(
            source="model_predictions",
            sensitive_attributes=attr_names,
            n_samples=len(y_true),
            groups=[],
            fairness_results=[],
            overall_severity="pass",
            recommendations=["No intersectional groups met min_group_size threshold."],
        )

    # Disparate impact across all intersectional groups
    pos_rates = [g.pos_rate for g in groups]
    di_ratio = min(pos_rates) / max(pos_rates) if max(pos_rates) > 0 else 1.0
    accuracies = [g.accuracy for g in groups if g.accuracy is not None]
    acc_gap = max(accuracies) - min(accuracies) if accuracies else 0.0

    fairness_results = [
        FairnessResult(
            metric="intersectional_disparate_impact",
            value=round(di_ratio, 4),
            threshold=0.8,
            passed=di_ratio >= 0.8,
            detail={"n_groups": len(groups), "group_pos_rates": {g.group: g.pos_rate for g in groups}},
        ),
        FairnessResult(
            metric="intersectional_accuracy_gap",
            value=round(acc_gap, 4),
            threshold=0.1,
            passed=acc_gap <= 0.1,
            detail={"n_groups": len(groups)},
        ),
    ]

    n_failed = sum(1 for r in fairness_results if not r.passed)
    severity = "pass" if n_failed == 0 else ("fail" if n_failed >= 2 else "warning")

    if not fairness_results[0].passed:
        recommendations.append(
            "Intersectional disparate impact detected. "
            "Combined sensitive attributes create compounded disadvantage."
        )

    return BiasReport(
        source="model_predictions",
        sensitive_attributes=attr_names,
        n_samples=len(y_true),
        groups=groups,
        fairness_results=fairness_results,
        overall_severity=severity,
        recommendations=recommendations,
    )


# ═══════════════════════════════════════════════════════════════
# Decision fairness (policy-level audit)
# ═══════════════════════════════════════════════════════════════

def audit_decision_fairness(
    decisions: np.ndarray,        # binary decisions (accept/reject, approve/deny)
    sensitive: np.ndarray,
    group_names: list[str] | None = None,
) -> BiasReport:
    """
    Audit decision outcomes for fairness (approval rates, rejection patterns).

    Use when you have final decisions (not predictions), e.g.:
      - Loan approval/rejection
      - Resume screening pass/fail
      - Moderation flag/unflag
    """
    decisions = np.asarray(decisions).ravel()
    sensitive = np.asarray(sensitive).ravel()
    unique_groups = sorted(set(sensitive))

    if group_names is None:
        group_names = [str(g) for g in unique_groups]

    n_total = len(decisions)
    n_groups = len(unique_groups)

    groups: list[GroupMetrics] = []
    for g, name in zip(unique_groups, group_names):
        mask = sensitive == g
        count = int(mask.sum())
        pos_rate = float(decisions[mask].mean())  # approval rate
        groups.append(GroupMetrics(group=name, count=count, pos_rate=pos_rate))

    pos_rates = [g.pos_rate for g in groups]
    di_ratio = min(pos_rates) / max(pos_rates) if max(pos_rates) > 0 else 1.0
    spd = max(pos_rates) - min(pos_rates)

    fairness_results = [
        FairnessResult(
            metric="disparate_impact",
            value=round(di_ratio, 4),
            threshold=0.8,
            passed=di_ratio >= 0.8,
            detail={"per_group": {g.group: round(g.pos_rate, 4) for g in groups}},
        ),
        FairnessResult(
            metric="statistical_parity_difference",
            value=round(spd, 4),
            threshold=0.1,
            passed=spd <= 0.1,
        ),
    ]

    recommendations: list[str] = []
    if not fairness_results[0].passed:
        recommendations.append(
            f"Decision outcomes show disparate impact "
            f"(DI={di_ratio:.3f} < 0.80). Review decision policy for fairness."
        )

    severity = "pass"
    if not fairness_results[0].passed or not fairness_results[1].passed:
        severity = "fail" if di_ratio < 0.5 else "warning"

    return BiasReport(
        source="model_predictions",
        sensitive_attributes=[str(g) for g in unique_groups],
        n_samples=n_total,
        groups=groups,
        fairness_results=fairness_results,
        overall_severity=severity,
        recommendations=recommendations,
    )


# ═══════════════════════════════════════════════════════════════
# Report export
# ═══════════════════════════════════════════════════════════════

def export_bias_report(report: BiasReport, output_dir: str = None) -> str:
    """Export a BiasReport as JSON to the fairness workspace directory."""
    if output_dir is None:
        output_dir = f"workspace/测试报告/{os.getenv('PROJECT_NAME', 'default')}/ai-fairness"
    from datetime import datetime

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output_dir) / f"bias_report_{ts}.json"

    data = {
        "source": report.source,
        "sensitive_attributes": report.sensitive_attributes,
        "n_samples": report.n_samples,
        "overall_severity": report.overall_severity,
        "groups": [
            {
                "group": g.group,
                "count": g.count,
                "pos_rate": g.pos_rate,
                "accuracy": g.accuracy,
                "tpr": g.tpr,
                "fpr": g.fpr,
                "precision": g.precision,
                "calibration": g.calibration,
            }
            for g in report.groups
        ],
        "fairness_results": [
            {
                "metric": r.metric,
                "value": r.value,
                "threshold": r.threshold,
                "passed": r.passed,
                "detail": r.detail,
            }
            for r in report.fairness_results
        ],
        "recommendations": report.recommendations,
        "metadata": report.metadata,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Bias report exported to %s (severity=%s)", path, report.overall_severity)
    return str(path)


def summary(report: BiasReport) -> str:
    """One-line fairness summary suitable for CI logs."""
    status = {"pass": "PASS", "warning": "WARN", "fail": "FAIL"}
    lines = [f"Fairness Audit [{status.get(report.overall_severity, report.overall_severity)}] "
             f"source={report.source} n={report.n_samples}"]
    for r in report.fairness_results:
        icon = "✓" if r.passed else "✗"
        lines.append(f"  {icon} {r.metric}: {r.value:.4f} (threshold={r.threshold})")
    if report.recommendations:
        lines.append(f"  Recommendations ({len(report.recommendations)}):")
        for rec in report.recommendations:
            lines.append(f"    - {rec}")
    return "\n".join(lines)
