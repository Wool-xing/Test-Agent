"""User journey impact mapping — link test results to business journeys.

Helps answer: "If this test fails, what user journeys are affected?"
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Default journey → module mapping (extend via workspace/journey_map.json)
DEFAULT_JOURNEYS: Dict[str, List[str]] = {
    "Registration": ["auth/register", "signup", "user/create"],
    "Login": ["auth/login", "session", "login"],
    "Payment": ["payment/", "order/", "checkout", "billing"],
    "Profile": ["user/profile", "account/settings", "profile"],
    "Search": ["search/", "catalog", "listing"],
    "Notifications": ["notification", "email", "push", "sms"],
    "Admin": ["admin/", "dashboard", "manage"],
    "API": ["api/", "rest", "graphql", "endpoint"],
}


def load_journey_map(source: Optional[str | Path] = None) -> Dict[str, List[str]]:
    """Load journey map from JSON file, or use defaults."""
    if source:
        p = Path(source)
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("journeys", data)
    return dict(DEFAULT_JOURNEYS)


def map_failures_to_journeys(
    failures: List[Dict],
    journey_map: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, List[Dict]]:
    """Given a list of {name, ...} failures, return journeys → affected failures.

    Args:
        failures: list of {name: str, ...} from dashboard top_failures or expert heatmap.
        journey_map: optional custom mapping.

    Returns: {journey_name: [{name, fail_count, ...}]}
    """
    if journey_map is None:
        journey_map = load_journey_map()

    impacted: Dict[str, List[Dict]] = {}
    unmatched = list(failures)

    for journey, patterns in journey_map.items():
        matched = []
        for f in failures:
            name = f.get("name", "").lower()
            if any(p.lower() in name for p in patterns):
                matched.append(f)
        if matched:
            impacted[journey] = matched
            for m in matched:
                if m in unmatched:
                    unmatched.remove(m)

    if unmatched:
        impacted["Other"] = unmatched

    return impacted


def journey_impact_report(
    failures: List[Dict],
    journey_map: Optional[Dict[str, List[str]]] = None,
) -> Dict:
    """Generate full journey impact report.

    Returns:
        {
            "journeys_impacted": int,
            "total_failures": int,
            "by_journey": [{journey, failure_count, failures}],
            "most_impacted": str,  # journey with most failures
        }
    """
    impacted = map_failures_to_journeys(failures, journey_map)
    by_journey = [
        {
            "journey": j,
            "failure_count": len(flist),
            "failures": flist,
        }
        for j, flist in impacted.items()
    ]
    by_journey.sort(key=lambda x: -x["failure_count"])

    return {
        "journeys_impacted": len(by_journey),
        "total_failures": len(failures),
        "by_journey": by_journey,
        "most_impacted": by_journey[0]["journey"] if by_journey else "none",
    }


def to_markdown(report: Dict) -> str:
    lines = [
        "# Journey Impact Report",
        "",
        f"**Journeys impacted**: {report['journeys_impacted']} | "
        f"**Total failures**: {report['total_failures']} | "
        f"**Most impacted**: {report['most_impacted']}",
        "",
        "| Journey | Failures | Top Failing Expert |",
        "|---------|----------|-------------------|",
    ]
    for j in report["by_journey"]:
        top = j["failures"][0]["name"] if j["failures"] else "—"
        lines.append(f"| {j['journey']} | {j['failure_count']} | {top} |")
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────

def _cli() -> None:
    import argparse
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="User journey impact mapping")
    p.add_argument("--from-dashboard", action="store_true", help="Use live dashboard data")
    p.add_argument("--journey-map", help="Custom journey map JSON")
    p.add_argument("--markdown", action="store_true", help="Output markdown")
    args = p.parse_args()

    if args.from_dashboard:
        from runtime.observability.dashboard import build_dashboard
        data = build_dashboard(get_settings().workspace_dir)
        failures = data.get("diagnostic", {}).get("expert_heatmap", [])
    else:
        failures = [
            {"name": "mobile-tester", "fails": 3, "fail_rate_pct": 60},
            {"name": "automation-engineer", "fails": 2, "fail_rate_pct": 40},
            {"name": "bug-manager", "fails": 1, "fail_rate_pct": 20},
        ]

    jmap = load_journey_map(args.journey_map) if args.journey_map else None
    report = journey_impact_report(failures, jmap)

    if args.markdown:
        print(to_markdown(report))
    else:
        print(json.dumps(report, indent=2, ensure_ascii=False))


# Late import for CLI
from runtime.config.settings import get_settings  # noqa: E402


if __name__ == "__main__":
    _cli()
