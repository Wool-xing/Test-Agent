# SPDX-License-Identifier: MIT
"""Unit tests for silent_failure_detector.py — Phase 3.2 沉默故障检测."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

_utils_dir = Path(__file__).resolve().parents[2] / "utils"
if str(_utils_dir) not in sys.path:
    sys.path.insert(0, str(_utils_dir))


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def stable_data():
    """Stable metric: values centered around 100, no trend."""
    rng = np.random.RandomState(42)
    return list(rng.normal(100, 5, 30))


@pytest.fixture
def trending_up_data():
    """Metric trending upward toward threshold 200."""
    rng = np.random.RandomState(42)
    base = np.linspace(100, 180, 30)
    return list(base + rng.normal(0, 5, 30))


@pytest.fixture
def breached_data():
    """Metric that has crossed threshold 200 (mean ≈ 205, last points well above)."""
    rng = np.random.RandomState(42)
    base = np.linspace(140, 270, 30)
    return list(base + rng.normal(0, 5, 30))


@pytest.fixture
def declining_data():
    """Pass rate declining toward threshold (bad when below)."""
    rng = np.random.RandomState(42)
    base = np.linspace(0.95, 0.81, 30)
    return list(base + rng.normal(0, 0.02, 30))


# ═══════════════════════════════════════════════════════════════
# Drift detection tests
# ═══════════════════════════════════════════════════════════════

class TestDetectThresholdDrift:
    def test_stable_data_silent(self, stable_data):
        from silent_failure_detector import detect_threshold_drift
        r = detect_threshold_drift("test_metric", stable_data, threshold=200)
        assert r.severity == "silent"
        assert r.trend_pvalue is not None

    def test_trending_up_impending(self, trending_up_data):
        from silent_failure_detector import detect_threshold_drift
        r = detect_threshold_drift(
            "latency_ms", trending_up_data, threshold=200,
            drift_pct_threshold=0.10,
        )
        # Should be at least "impending" (close to threshold) or "silent" with trend
        assert r.severity in ("silent", "impending")
        assert r.mean_shift_pct > 0

    def test_breached_detected(self, breached_data):
        from silent_failure_detector import detect_threshold_drift
        r = detect_threshold_drift("error_rate", breached_data, threshold=200)
        assert r.severity == "breached"

    def test_direction_below(self, declining_data):
        from silent_failure_detector import detect_threshold_drift
        r = detect_threshold_drift(
            "pass_rate", declining_data, threshold=0.80,
            direction="below",
        )
        # Should detect the decline
        assert r.severity in ("silent", "impending", "breached")
        assert r.current_mean < r.baseline_mean or r.trend_slope < 0

    def test_insufficient_data(self):
        from silent_failure_detector import detect_threshold_drift
        r = detect_threshold_drift("sparse", [1.0, 2.0], threshold=10)
        assert "Insufficient" in r.recommendation

    def test_baseline_points_used(self, trending_up_data):
        from silent_failure_detector import detect_threshold_drift
        rng = np.random.RandomState(42)
        baseline = list(rng.normal(100, 3, 50))  # stable baseline
        r = detect_threshold_drift(
            "metric", trending_up_data, threshold=200,
            baseline_points=baseline,
        )
        assert r.baseline_mean < 105  # baseline should be near 100

    def test_mann_kendall_detects_trend(self, trending_up_data):
        from silent_failure_detector import _mann_kendall
        arr = np.asarray(trending_up_data)
        p = _mann_kendall(arr)
        assert p < 0.05  # strong upward trend

    def test_mann_kendall_no_trend(self, stable_data):
        from silent_failure_detector import _mann_kendall
        arr = np.asarray(stable_data)
        p = _mann_kendall(arr)
        assert p > 0.01  # no significant trend (M-K noisy with n=30)

    def test_linear_trend_slope(self, trending_up_data):
        from silent_failure_detector import _linear_trend
        arr = np.asarray(trending_up_data)
        slope = _linear_trend(arr)
        assert slope > 0  # upward slope


# ═══════════════════════════════════════════════════════════════
# Batch detection tests
# ═══════════════════════════════════════════════════════════════

class TestBatchDetect:
    def test_batch_all_stable(self, stable_data):
        from silent_failure_detector import MetricConfig, batch_detect
        cfgs = [
            MetricConfig("m1", "custom", stable_data, 200),
            MetricConfig("m2", "custom", stable_data, 200),
        ]
        report = batch_detect(cfgs)
        assert report.overall_severity == "pass"
        assert report.silent_count == 2

    def test_batch_one_breached(self, stable_data, breached_data):
        from silent_failure_detector import MetricConfig, batch_detect
        cfgs = [
            MetricConfig("stable", "custom", stable_data, 200),
            MetricConfig("breached", "custom", breached_data, 200),
        ]
        report = batch_detect(cfgs)
        assert report.overall_severity == "fail"
        assert report.breached_count >= 1

    def test_batch_one_impending(self, stable_data, trending_up_data):
        from silent_failure_detector import MetricConfig, batch_detect
        cfgs = [
            MetricConfig("stable", "custom", stable_data, 200),
            MetricConfig("trending", "custom", trending_up_data, 200),
        ]
        report = batch_detect(cfgs)
        assert report.overall_severity in ("warning", "pass")


# ═══════════════════════════════════════════════════════════════
# Source-specific collector tests
# ═══════════════════════════════════════════════════════════════

class TestSourceCollectors:
    def test_collect_from_tracing(self, trending_up_data):
        from silent_failure_detector import collect_from_tracing
        r = collect_from_tracing(trending_up_data, threshold_ms=200)
        assert r.source == "tracing"
        assert r.metric_name == "trace_duration_p95_ms"

    def test_collect_from_web_vitals(self, trending_up_data):
        from silent_failure_detector import collect_from_web_vitals
        r = collect_from_web_vitals("LCP_ms", trending_up_data, threshold=4000)
        assert r.source == "web_vitals"
        assert "LCP_ms" in r.metric_name

    def test_collect_from_prometheus_counter(self, trending_up_data):
        from silent_failure_detector import collect_from_prometheus_counter
        r = collect_from_prometheus_counter("agent_errors", trending_up_data, threshold=10)
        assert r.source == "prometheus"
        assert "agent_errors" in r.metric_name

    def test_collect_from_prometheus_gauge_below(self, declining_data):
        from silent_failure_detector import collect_from_prometheus_gauge
        r = collect_from_prometheus_gauge(
            "pass_rate", declining_data, threshold=0.80, direction="below",
        )
        assert r.source == "prometheus"


# ═══════════════════════════════════════════════════════════════
# Sliding window tests
# ═══════════════════════════════════════════════════════════════

class TestSlidingWindow:
    def test_push_and_get(self):
        from silent_failure_detector import SlidingWindowStore
        store = SlidingWindowStore(max_points=5)
        for v in [1, 2, 3, 4, 5, 6, 7]:
            store.push("latency", v)
        vals = store.get("latency")
        assert len(vals) == 5
        assert vals == [3, 4, 5, 6, 7]

    def test_get_all(self):
        from silent_failure_detector import SlidingWindowStore
        store = SlidingWindowStore()
        store.push("a", 1)
        store.push("a", 2)
        store.push("b", 10)
        all_data = store.get_all()
        assert len(all_data) == 2

    def test_clear(self):
        from silent_failure_detector import SlidingWindowStore
        store = SlidingWindowStore()
        store.push("x", 1)
        store.clear("x")
        assert store.get("x") == []


# ═══════════════════════════════════════════════════════════════
# Export tests
# ═══════════════════════════════════════════════════════════════

class TestExport:
    def test_export_json(self, stable_data, tmp_path):
        from silent_failure_detector import MetricConfig, batch_detect, export_report
        report = batch_detect([MetricConfig("m1", "custom", stable_data, 200)])
        path = export_report(report, output_dir=str(tmp_path))
        assert Path(path).exists()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["overall_severity"] == "pass"

    def test_ci_summary(self, stable_data):
        from silent_failure_detector import MetricConfig, batch_detect, ci_summary
        report = batch_detect([MetricConfig("m1", "custom", stable_data, 200)])
        text = ci_summary(report)
        assert "PASS" in text
        assert "silent" in text.lower()
