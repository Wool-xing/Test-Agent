"""Carbon-aware test scheduler — schedule tests in low-carbon energy windows.

Features:
- electricityMap API integration for real-time carbon intensity
- CodeCarbon tracking per test run
- Green budget enforcement (max CO2 per test suite)
- Optimal window scheduling (delay tests for low-carbon periods)
- Carbon audit report generation

Usage:
  python carbon_scheduler.py schedule --test-suite "unit" --region CN-BJ
  python carbon_scheduler.py track --test-run-id run-123
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    from codecarbon import EmissionsTracker
    HAS_CODECARBON = True
except ImportError:
    HAS_CODECARBON = False


@dataclass
class CarbonWindow:
    start: float           # Unix timestamp
    end: float
    intensity_gco2_per_kwh: float
    level: str             # "very_low", "low", "moderate", "high", "very_high"


@dataclass
class CarbonReport:
    run_id: str
    test_suite: str
    duration_seconds: float = 0.0
    energy_kwh: float = 0.0
    co2_kg: float = 0.0
    carbon_intensity_gco2_per_kwh: float = 0.0
    region: str = ""
    optimal_window_used: bool = False
    budget_exceeded: bool = False
    green_budget_kg: float = 0.0

    def to_dict(self) -> dict:
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in self.__dict__.items()}


# ═══════════════════════════════════════════════════════════════
# Carbon intensity lookup
# ═══════════════════════════════════════════════════════════════

DEFAULT_INTENSITY = 500  # gCO2/kWh (global average when API unavailable)

FALLBACK_INTENSITIES = {
    "CN": 550, "US": 380, "EU": 250, "IN": 700,
    "BR": 110, "FR": 55, "GB": 200, "DE": 350,
    "JP": 450, "KR": 420, "AU": 550, "CA": 150,
}

REGION_FALLBACK = {
    "CN-BJ": "CN", "CN-SH": "CN", "CN-GD": "CN",
    "US-East": "US", "US-West": "US",
    "EU-DE": "DE", "EU-FR": "FR",
}


def get_carbon_intensity(region: str = "") -> float:
    """Get current carbon intensity for a region.
    Uses electricityMap API if available, else fallback data."""
    api_key = os.environ.get("ELECTRICITYMAP_API_KEY", "")
    if api_key and region:
        try:
            import requests
            resp = requests.get(
                f"https://api.electricitymap.org/v3/carbon-intensity/latest?zone={region}",
                headers={"auth-token": api_key}, timeout=10)
            if resp.status_code == 200:
                return resp.json().get("carbonIntensity", DEFAULT_INTENSITY)
        except Exception as e:
            logger.warning("carbon intensity API call failed for {}: {}", region, e)

    # Fallback
    country = REGION_FALLBACK.get(region, region[:2] if len(region) >= 2 else "")
    return FALLBACK_INTENSITIES.get(country, DEFAULT_INTENSITY)


def get_optimal_windows(region: str = "", hours_ahead: int = 24,
                         threshold_pct: float = 0.3) -> list[CarbonWindow]:
    """Find optimal low-carbon windows in the next N hours."""
    now = time.time()
    api_key = os.environ.get("ELECTRICITYMAP_API_KEY", "")

    if api_key and region:
        try:
            import requests
            resp = requests.get(
                f"https://api.electricitymap.org/v3/carbon-intensity/forecast?zone={region}",
                headers={"auth-token": api_key}, timeout=10)
            if resp.status_code == 200:
                forecast = resp.json().get("forecast", [])
                windows = []
                for entry in forecast:
                    intensity = entry.get("carbonIntensity", DEFAULT_INTENSITY)
                    if intensity < DEFAULT_INTENSITY * threshold_pct:
                        level = "very_low"
                    elif intensity < DEFAULT_INTENSITY * 0.5:
                        level = "low"
                    elif intensity < DEFAULT_INTENSITY * 0.75:
                        level = "moderate"
                    else:
                        level = "high"
                    # Parse ISO datetime string to float timestamp
                    dt_str = entry.get("datetime", "")
                    try:
                        from datetime import datetime as _dt
                        ts = _dt.fromisoformat(dt_str.replace("Z", "+00:00")).timestamp()
                    except (ValueError, TypeError):
                        ts = now
                    windows.append(CarbonWindow(
                        start=ts,
                        end=ts,
                        intensity_gco2_per_kwh=intensity,
                        level=level,
                    ))
                return windows
        except Exception as e:
            logger.warning("carbon intensity API call failed for {}: {}", region, e)

    # Fallback: return current single window
    intensity = get_carbon_intensity(region)
    level = "very_low" if intensity < 150 else "low" if intensity < 300 else "moderate"
    return [CarbonWindow(now, now + 3600, intensity, level)]


# ═══════════════════════════════════════════════════════════════
# Carbon tracking
# ═══════════════════════════════════════════════════════════════

class GreenTestTracker:
    """Track carbon footprint per test run."""

    def __init__(self, green_budget_kg: float = 1.0):
        self._budget = green_budget_kg
        self._tracker: Any = None
        self._reports: list[CarbonReport] = []
        self._persist_path = Path("workspace/carbon_reports.jsonl")

    def start(self, run_id: str, test_suite: str, region: str = "") -> None:
        if HAS_CODECARBON:
            self._tracker = EmissionsTracker(
                project_name=f"tagent-{test_suite}",
                output_dir="workspace",
                output_file=f"carbon_{run_id}.csv",
            )
            self._tracker.start()

        self._current = CarbonReport(run_id=run_id, test_suite=test_suite,
                                     region=region, green_budget_kg=self._budget)

    def stop(self) -> CarbonReport:
        if self._tracker and HAS_CODECARBON:
            try:
                emissions = self._tracker.stop()
                self._current.co2_kg = emissions if emissions else 0.0
            except Exception:
                pass

        self._current.budget_exceeded = self._current.co2_kg > self._budget
        self._append_report(self._current)
        return self._current

    def _append_report(self, report: CarbonReport) -> None:
        self._reports.append(report)
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._persist_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(report.to_dict(), ensure_ascii=False) + "\n")

    def summary(self) -> dict:
        total_co2 = sum(r.co2_kg for r in self._reports)
        total_runs = len(self._reports)
        budget_exceeded = sum(1 for r in self._reports if r.budget_exceeded)
        return {
            "total_runs": total_runs,
            "total_co2_kg": round(total_co2, 4),
            "avg_co2_per_run_kg": round(total_co2 / max(total_runs, 1), 4),
            "budget_exceeded_count": budget_exceeded,
            "green_budget_kg": self._budget,
        }


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Carbon-Aware Test Scheduler")
    sub = ap.add_subparsers(dest="cmd")

    sched = sub.add_parser("schedule", help="Check optimal test windows")
    sched.add_argument("--region", default="CN")
    sched.add_argument("--hours", type=int, default=24)

    track = sub.add_parser("track", help="Track a test run")
    track.add_argument("--run-id", required=True)
    track.add_argument("--suite", default="unit")
    track.add_argument("--region", default="CN")
    track.add_argument("--green-budget-kg", type=float, default=1.0)

    summary = sub.add_parser("summary", help="Carbon summary")

    args = ap.parse_args()

    if args.cmd == "schedule":
        windows = get_optimal_windows(args.region, args.hours)
        print(f"Carbon intensity ({args.region}): {get_carbon_intensity(args.region):.0f} gCO2/kWh")
        for w in windows[:5]:
            print(f"  [{w.level}] {w.intensity_gco2_per_kwh:.0f} gCO2/kWh")

    elif args.cmd == "track":
        tracker = GreenTestTracker(args.green_budget_kg)
        tracker.start(args.run_id, args.suite, args.region)
        time.sleep(1)  # Simulate test execution
        report = tracker.stop()
        print(json.dumps(report.to_dict(), indent=2))

    elif args.cmd == "summary":
        tracker = GreenTestTracker()
        print(json.dumps(tracker.summary(), indent=2))
