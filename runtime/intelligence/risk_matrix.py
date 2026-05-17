"""Quantitative risk matrix — calibrated probability × impact with mitigation tracking.

ISTQB‑aligned. Standalone module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class RiskItem:
    id: str
    description: str
    probability: float   # 0.0 – 1.0 (calibrated)
    impact: float         # 0.0 – 1.0 (calibrated)
    category: str = "functional"
    mitigations: List[str] = field(default_factory=list)
    residual_probability: float | None = None
    residual_impact: float | None = None

    @property
    def exposure(self) -> float:
        return round(self.probability * self.impact, 3)

    @property
    def residual_exposure(self) -> float | None:
        if self.residual_probability is not None and self.residual_impact is not None:
            return round(self.residual_probability * self.residual_impact, 3)
        return None

    @property
    def level(self) -> str:
        """Risk level based on calibrated exposure."""
        e = self.exposure
        if e >= 0.50:
            return "CRITICAL"
        if e >= 0.25:
            return "HIGH"
        if e >= 0.10:
            return "MEDIUM"
        return "LOW"


@dataclass
class RiskMatrix:
    items: List[RiskItem] = field(default_factory=list)

    def add(self, item: RiskItem) -> None:
        self.items.append(item)

    def calibrate(self, historical_fail_rate: float = 0.05) -> None:
        """Apply base‑rate calibration to probability estimates."""
        for item in self.items:
            # Simple Bayesian calibration: shrink towards base rate
            n = 3  # effective sample size
            item.probability = round((item.probability * n + historical_fail_rate) / (n + 1), 3)

    def mitigate(self, item_id: str, residual_prob: float, residual_impact: float, mitigations: List[str]) -> None:
        for item in self.items:
            if item.id == item_id:
                item.residual_probability = residual_prob
                item.residual_impact = residual_impact
                item.mitigations.extend(mitigations)
                return
        raise KeyError(f"risk item '{item_id}' not found")

    def summary(self) -> Dict:
        levels = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for item in self.items:
            levels[item.level] += 1
        total_exposure = sum(item.exposure for item in self.items)
        mitigated = sum(1 for item in self.items if item.residual_exposure is not None)
        residual_total = sum(item.residual_exposure for item in self.items if item.residual_exposure is not None)
        return {
            "total_items": len(self.items),
            "by_level": levels,
            "total_exposure": round(total_exposure, 3),
            "mitigated_count": mitigated,
            "residual_exposure": round(residual_total, 3) if mitigated else None,
            "risk_reduction_pct": round((1 - residual_total / total_exposure) * 100, 1) if mitigated and total_exposure > 0 else None,
            "items": [
                {
                    "id": item.id,
                    "description": item.description,
                    "category": item.category,
                    "probability": item.probability,
                    "impact": item.impact,
                    "exposure": item.exposure,
                    "level": item.level,
                    "mitigations": item.mitigations,
                    "residual_exposure": item.residual_exposure,
                }
                for item in sorted(self.items, key=lambda x: -x.exposure)
            ],
        }

    def to_markdown(self) -> str:
        s = self.summary()
        lines = [
            "# Risk Matrix",
            "",
            f"**Total**: {s['total_items']} risks | "
            f"**Exposure**: {s['total_exposure']} | "
            f"**Mitigated**: {s['mitigated_count']}/{s['total_items']}",
            "",
            f"| {'CRITICAL':8} | {'HIGH':8} | {'MEDIUM':8} | {'LOW':8} |",
            f"|{':---:'.join(['-'*8]*4)}|",
            f"| {s['by_level']['CRITICAL']:8} | {s['by_level']['HIGH']:8} | {s['by_level']['MEDIUM']:8} | {s['by_level']['LOW']:8} |",
            "",
            "| ID | Description | Cat | Prob | Impact | Exposure | Level | Residual |",
            "|----|------------|-----|------|--------|----------|-------|----------|",
        ]
        for item in s["items"]:
            res = f"{item['residual_exposure']:.3f}" if item["residual_exposure"] is not None else "—"
            lines.append(
                f"| {item['id']} | {item['description'][:40]} | {item['category']} | "
                f"{item['probability']:.2f} | {item['impact']:.2f} | {item['exposure']:.3f} | "
                f"{item['level']} | {res} |"
            )
        if s["risk_reduction_pct"] is not None:
            lines.append(f"\n**Risk reduction after mitigation: {s['risk_reduction_pct']}%**")
        return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────

def _cli() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Quantitative risk matrix")
    p.add_argument("--load", help="Load risks from JSON file")
    p.add_argument("--calibrate", type=float, default=0.05, help="Base rate for calibration")
    p.add_argument("--markdown", action="store_true", help="Output markdown table")
    args = p.parse_args()

    matrix = RiskMatrix()

    if args.load:
        data = json.loads(Path(args.load).read_text(encoding="utf-8"))
        for r in data.get("risks", data if isinstance(data, list) else []):
            matrix.add(RiskItem(
                id=r["id"], description=r["description"],
                probability=r["probability"], impact=r["impact"],
                category=r.get("category", "functional"),
                mitigations=r.get("mitigations", []),
                residual_probability=r.get("residual_probability"),
                residual_impact=r.get("residual_impact"),
            ))
    else:
        # Demo risks
        matrix.add(RiskItem("R1", "LLM API timeout during test execution", 0.3, 0.8, "reliability"))
        matrix.add(RiskItem("R2", "Flaky locator breaks after DOM change", 0.4, 0.6, "maintainability"))
        matrix.add(RiskItem("R3", "Concurrent DAG runs share workspace", 0.1, 0.9, "functional"))
        matrix.add(RiskItem("R4", "Unsanitized user PRD file causes SSRF", 0.05, 0.95, "security"))
        matrix.add(RiskItem("R5", "Prefect server unavailable", 0.15, 0.7, "reliability"))

    if args.calibrate:
        matrix.calibrate(args.calibrate)

    if args.markdown:
        print(matrix.to_markdown())
    else:
        print(json.dumps(matrix.summary(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli()
