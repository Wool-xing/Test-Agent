# SPDX-License-Identifier: MIT
"""Unit tests for fairness_auditor.py — Phase 3.1 伦理/偏见审计."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# utils package installed via pip install -e runtime/


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def balanced_dataset():
    """Two groups, exactly equal representation, exactly equal label rates."""
    # Group 0: 50 positive, 50 negative
    y0 = np.array([1] * 50 + [0] * 50, dtype=float)
    # Group 1: 50 positive, 50 negative (same distribution)
    y1 = np.array([1] * 50 + [0] * 50, dtype=float)
    y_true = np.concatenate([y0, y1])
    sensitive = np.array([0] * 100 + [1] * 100)
    return y_true, sensitive


@pytest.fixture
def biased_dataset():
    """Group 0 overrepresented, group 0 has higher positive rate."""
    rng = np.random.RandomState(42)
    n_a, n_b = 160, 40  # 80/20 split
    y_a = rng.choice([0, 1], n_a, p=[0.3, 0.7])  # 70% positive
    y_b = rng.choice([0, 1], n_b, p=[0.7, 0.3])  # 30% positive
    y_true = np.concatenate([y_a, y_b]).astype(float)
    sensitive = np.array([0] * n_a + [1] * n_b)
    return y_true, sensitive


@pytest.fixture
def fair_predictions():
    """Predictions that are perfectly fair across groups — exact same positive rate."""
    # Group 0: 50 positive, 50 negative
    y0 = np.array([1] * 50 + [0] * 50, dtype=float)
    # Group 1: 50 positive, 50 negative (same distribution)
    y1 = np.array([1] * 50 + [0] * 50, dtype=float)
    y_true = np.concatenate([y0, y1])
    y_pred = y_true.copy()  # perfect predictions
    sensitive = np.array([0] * 100 + [1] * 100)
    return y_true, y_pred, sensitive


@pytest.fixture
def biased_predictions():
    """Predictions biased against group 1."""
    rng = np.random.RandomState(42)
    n_a, n_b = 100, 100
    # Group 0: perfect prediction
    yt_a = rng.randint(0, 2, n_a).astype(float)
    yp_a = yt_a.copy()
    # Group 1: 30% false negative rate
    yt_b = rng.randint(0, 2, n_b).astype(float)
    yp_b = yt_b.copy()
    fn_mask = (yt_b == 1) & (rng.random(n_b) < 0.3)
    yp_b[fn_mask] = 0
    y_true = np.concatenate([yt_a, yt_b]).astype(float)
    y_pred = np.concatenate([yp_a, yp_b]).astype(float)
    sensitive = np.array([0] * n_a + [1] * n_b)
    return y_true, y_pred, sensitive


# ═══════════════════════════════════════════════════════════════
# Dataset bias tests
# ═══════════════════════════════════════════════════════════════

class TestAuditDatasetBias:
    def test_balanced_dataset_passes(self, balanced_dataset):
        from utils.a11y_i18n.fairness_auditor import audit_dataset_bias
        y_true, sensitive = balanced_dataset
        report = audit_dataset_bias(y_true, sensitive, group_names=["A", "B"])
        assert report.overall_severity == "pass"
        assert report.source == "dataset"

    def test_biased_dataset_detects_representation_gap(self, biased_dataset):
        from utils.a11y_i18n.fairness_auditor import audit_dataset_bias
        y_true, sensitive = biased_dataset
        report = audit_dataset_bias(y_true, sensitive, group_names=["A", "B"],
                                    representation_threshold=0.15)
        assert report.overall_severity in ("warning", "fail")
        repr_result = next(r for r in report.fairness_results
                          if r.metric == "representation_parity")
        assert not repr_result.passed

    def test_biased_dataset_detects_label_imbalance(self, biased_dataset):
        from utils.a11y_i18n.fairness_auditor import audit_dataset_bias
        y_true, sensitive = biased_dataset
        report = audit_dataset_bias(y_true, sensitive, group_names=["A", "B"])
        label_result = next(r for r in report.fairness_results
                           if r.metric == "label_balance")
        assert not label_result.passed

    def test_recommendations_generated_for_biased(self, biased_dataset):
        from utils.a11y_i18n.fairness_auditor import audit_dataset_bias
        y_true, sensitive = biased_dataset
        report = audit_dataset_bias(y_true, sensitive, group_names=["A", "B"])
        assert len(report.recommendations) > 0

    def test_mismatched_group_names_raises(self, balanced_dataset):
            with pytest.raises(ValueError): check_fairness(groups=['a'], references=['b'])
        from utils.a11y_i18n.fairness_auditor import audit_dataset_bias
        y_true, sensitive = balanced_dataset
        with pytest.raises(ValueError):
            audit_dataset_bias(y_true, sensitive, group_names=["only_one"])

    def test_repr_custom_threshold(self, biased_dataset):
        from utils.a11y_i18n.fairness_auditor import audit_dataset_bias
        y_true, sensitive = biased_dataset
        # Very permissive threshold → should pass
        report = audit_dataset_bias(y_true, sensitive, group_names=["A", "B"],
                                    representation_threshold=0.5)
        repr_result = next(r for r in report.fairness_results
                          if r.metric == "representation_parity")
        assert repr_result.passed


# ═══════════════════════════════════════════════════════════════
# Model fairness tests
# ═══════════════════════════════════════════════════════════════

class TestAuditModelFairness:
    def test_perfect_predictions_pass_all_metrics(self, fair_predictions):
        from utils.a11y_i18n.fairness_auditor import audit_model_fairness
        y_true, y_pred, sensitive = fair_predictions
        report = audit_model_fairness(y_true, y_pred, sensitive, group_names=["A", "B"])
        assert report.overall_severity == "pass"
        assert all(r.passed for r in report.fairness_results)

    def test_biased_predictions_detected(self, biased_predictions):
        from utils.a11y_i18n.fairness_auditor import audit_model_fairness
        y_true, y_pred, sensitive = biased_predictions
        report = audit_model_fairness(y_true, y_pred, sensitive, group_names=["A", "B"])
        # At least equal_opportunity should fail (TPR gap)
        assert report.overall_severity in ("warning", "fail")

    def test_disparate_impact_computed(self, fair_predictions):
        from utils.a11y_i18n.fairness_auditor import audit_model_fairness
        y_true, y_pred, sensitive = fair_predictions
        report = audit_model_fairness(y_true, y_pred, sensitive, group_names=["A", "B"])
        di = next(r for r in report.fairness_results if r.metric == "disparate_impact")
        assert di.value > 0.0
        assert di.value <= 1.0

    def test_group_metrics_populated(self, fair_predictions):
        from utils.a11y_i18n.fairness_auditor import audit_model_fairness
        y_true, y_pred, sensitive = fair_predictions
        report = audit_model_fairness(y_true, y_pred, sensitive, group_names=["X", "Y"])
        assert len(report.groups) == 2
        for g in report.groups:
            assert g.count > 0
            assert g.tpr is not None
            assert g.fpr is not None

    def test_all_6_metrics_present(self, biased_predictions):
        from utils.a11y_i18n.fairness_auditor import audit_model_fairness
        y_true, y_pred, sensitive = biased_predictions
        report = audit_model_fairness(y_true, y_pred, sensitive, group_names=["A", "B"])
        metric_names = {r.metric for r in report.fairness_results}
        expected = {"disparate_impact", "statistical_parity_difference",
                    "equal_opportunity", "equalized_odds",
                    "calibration_parity", "predictive_parity"}
        assert expected.issubset(metric_names)


# ═══════════════════════════════════════════════════════════════
# Intersectional fairness tests
# ═══════════════════════════════════════════════════════════════

class TestAuditIntersectional:
    @pytest.fixture
    def intersectional_data(self):
        rng = np.random.RandomState(42)
        n = 200
        y_true = rng.randint(0, 2, n).astype(float)
        # Gender: half 0, half 1
        gender = np.array([0] * 100 + [1] * 100)
        # Race: 0 for first 60 + last 50, 1 for middle 90
        race = np.array([0] * 60 + [1] * 40 + [0] * 50 + [1] * 50)
        y_pred = y_true.copy()
        # Bias: gender=1 & race=1 get worse predictions
        mask = (gender == 1) & (race == 1)
        y_pred[mask] = rng.choice([0, 1], mask.sum(), p=[0.4, 0.6])
        return y_true, y_pred, {"gender": gender, "race": race}

    def test_intersectional_groups_created(self, intersectional_data):
        from utils.a11y_i18n.fairness_auditor import audit_intersectional
        y_true, y_pred, sensitive = intersectional_data
        report = audit_intersectional(y_true, y_pred, sensitive, min_group_size=5)
        assert len(report.groups) >= 2

    def test_intersectional_metrics_present(self, intersectional_data):
        from utils.a11y_i18n.fairness_auditor import audit_intersectional
        y_true, y_pred, sensitive = intersectional_data
        report = audit_intersectional(y_true, y_pred, sensitive, min_group_size=5)
        metric_names = {r.metric for r in report.fairness_results}
        assert "intersectional_disparate_impact" in metric_names
        assert "intersectional_accuracy_gap" in metric_names

    def test_small_groups_filtered(self, intersectional_data):
        from utils.a11y_i18n.fairness_auditor import audit_intersectional
        y_true, y_pred, sensitive = intersectional_data
        # With high min_group_size, all groups should be filtered
        report = audit_intersectional(y_true, y_pred, sensitive, min_group_size=1000)
        assert report.overall_severity == "pass"
        assert len(report.groups) == 0


# ═══════════════════════════════════════════════════════════════
# Decision fairness tests
# ═══════════════════════════════════════════════════════════════

class TestAuditDecisionFairness:
    def test_fair_decisions_pass(self):
        from utils.a11y_i18n.fairness_auditor import audit_decision_fairness
        rng = np.random.RandomState(42)
        decisions = rng.choice([0, 1], 200, p=[0.5, 0.5]).astype(float)
        sensitive = np.array([0] * 100 + [1] * 100)
        report = audit_decision_fairness(decisions, sensitive, group_names=["A", "B"])
        # With random decisions and equal groups, should be close to fair
        assert report.overall_severity in ("pass", "warning")

    def test_biased_decisions_detected(self):
        from utils.a11y_i18n.fairness_auditor import audit_decision_fairness
        rng = np.random.RandomState(42)
        # Group 0: 80% approved, Group 1: 20% approved
        d0 = rng.choice([0, 1], 100, p=[0.2, 0.8]).astype(float)
        d1 = rng.choice([0, 1], 100, p=[0.8, 0.2]).astype(float)
        decisions = np.concatenate([d0, d1])
        sensitive = np.array([0] * 100 + [1] * 100)
        report = audit_decision_fairness(decisions, sensitive, group_names=["A", "B"])
        assert report.overall_severity == "fail"

    def test_decision_groups_match(self):
        from utils.a11y_i18n.fairness_auditor import audit_decision_fairness
        decisions = np.array([1, 1, 0, 0, 1, 0])
        sensitive = np.array([0, 0, 0, 1, 1, 1])
        report = audit_decision_fairness(decisions, sensitive, group_names=["X", "Y"])
        assert len(report.groups) == 2
        assert report.groups[0].count == 3
        assert report.groups[1].count == 3


# ═══════════════════════════════════════════════════════════════
# Export and summary tests
# ═══════════════════════════════════════════════════════════════

class TestExport:
    def test_export_creates_file(self, balanced_dataset, tmp_path):
        from utils.a11y_i18n.fairness_auditor import audit_dataset_bias, export_bias_report
        y_true, sensitive = balanced_dataset
        report = audit_dataset_bias(y_true, sensitive, group_names=["A", "B"])
        path = export_bias_report(report, output_dir=str(tmp_path))
        assert Path(path).exists()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["overall_severity"] == "pass"
        assert data["source"] == "dataset"
        assert len(data["fairness_results"]) == 2

    def test_summary_contains_metrics(self, fair_predictions):
        from utils.a11y_i18n.fairness_auditor import audit_model_fairness, summary
        y_true, y_pred, sensitive = fair_predictions
        report = audit_model_fairness(y_true, y_pred, sensitive, group_names=["A", "B"])
        text = summary(report)
        assert "disparate_impact" in text
        assert "equal_opportunity" in text

    def test_summary_shows_severity(self, fair_predictions):
        from utils.a11y_i18n.fairness_auditor import audit_model_fairness, summary
        y_true, y_pred, sensitive = fair_predictions
        report = audit_model_fairness(y_true, y_pred, sensitive, group_names=["A", "B"])
        text = summary(report)
        assert "PASS" in text
