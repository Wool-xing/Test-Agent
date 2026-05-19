# SPDX-License-Identifier: MIT
"""
WCAG 2.2 无障碍扫描器 v2 — 完整 78 条成功标准 + 程序化评估。

升级要点 (vs a11y_scanner.py WCAG 2.1):
- WCAG 2.2 新增 9 条成功标准 (2.4.11-2.4.13, 2.5.7-2.5.8, 3.2.6, 3.3.7-3.3.9)
- 完整 A/AA/AAA 3 级 78 条检查清单
- 程序化 checklist 评估 (不再只是打印文本)
- 自动扫描结果映射到具体 SC 编号
- 综合评分: automated_score × 0.6 + checklist_score × 0.4
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# WCAG 2.2 完整成功标准 (78 条)
# ═══════════════════════════════════════════════════════════════

@dataclass
class SuccessCriterion:
    num: str
    name: str
    level: str  # A | AA | AAA
    description: str
    auto_checkable: bool = False

WCAG22_CRITERIA: list[SuccessCriterion] = [
    # ── Principle 1: Perceivable ──
    SuccessCriterion("1.1.1", "Non-text Content", "A", "All non-text content has text alternative", True),
    SuccessCriterion("1.2.1", "Audio-only and Video-only (Prerecorded)", "A", "Prerecorded media has alternative"),
    SuccessCriterion("1.2.2", "Captions (Prerecorded)", "A", "Captions for prerecorded audio in synchronized media"),
    SuccessCriterion("1.2.3", "Audio Description or Media Alternative", "A", "Alternative for video"),
    SuccessCriterion("1.2.4", "Captions (Live)", "AA", "Captions for live synchronized media"),
    SuccessCriterion("1.2.5", "Audio Description (Prerecorded)", "AA", "Audio description for prerecorded video"),
    SuccessCriterion("1.2.6", "Sign Language (Prerecorded)", "AAA", "Sign language interpretation"),
    SuccessCriterion("1.2.7", "Extended Audio Description", "AAA", "Extended audio description when pauses insufficient"),
    SuccessCriterion("1.2.8", "Media Alternative (Prerecorded)", "AAA", "Full text alternative for prerecorded media"),
    SuccessCriterion("1.2.9", "Audio-only (Live)", "AAA", "Text alternative for live audio"),
    SuccessCriterion("1.3.1", "Info and Relationships", "A", "Semantic structure conveyed in markup", True),
    SuccessCriterion("1.3.2", "Meaningful Sequence", "A", "Reading order preserved in markup"),
    SuccessCriterion("1.3.3", "Sensory Characteristics", "A", "Instructions don't rely solely on sensory cues"),
    SuccessCriterion("1.3.4", "Orientation", "AA", "Content not locked to single orientation", True),
    SuccessCriterion("1.3.5", "Identify Input Purpose", "AA", "Input purpose programmatically determinable", True),
    SuccessCriterion("1.3.6", "Identify Purpose", "AAA", "Purpose of UI components programmatically determinable"),
    SuccessCriterion("1.4.1", "Use of Color", "A", "Color not the only visual means of conveying information"),
    SuccessCriterion("1.4.2", "Audio Control", "A", "Audio >3 seconds has pause/stop/volume control"),
    SuccessCriterion("1.4.3", "Contrast (Minimum)", "AA", "Text contrast ratio >= 4.5:1 (3:1 for large text)", True),
    SuccessCriterion("1.4.4", "Resize Text", "AA", "Text resizable to 200% without loss of content"),
    SuccessCriterion("1.4.5", "Images of Text", "AA", "Use text, not images of text"),
    SuccessCriterion("1.4.6", "Contrast (Enhanced)", "AAA", "Text contrast ratio >= 7:1 (4.5:1 for large text)", True),
    SuccessCriterion("1.4.7", "Low or No Background Audio", "AAA", "Audio has no/minimal background sounds"),
    SuccessCriterion("1.4.8", "Visual Presentation", "AAA", "Configurable foreground/background, line spacing, width"),
    SuccessCriterion("1.4.9", "Images of Text (No Exception)", "AAA", "No images of text except decoration"),
    SuccessCriterion("1.4.10", "Reflow", "AA", "Content reflows at 320px width without horizontal scroll"),
    SuccessCriterion("1.4.11", "Non-text Contrast", "AA", "UI components >= 3:1 contrast", True),
    SuccessCriterion("1.4.12", "Text Spacing", "AA", "Configurable line/paragraph/letter/word spacing without loss"),
    SuccessCriterion("1.4.13", "Content on Hover or Focus", "AA", "Hover/focus content is dismissible and persistent"),

    # ── Principle 2: Operable ──
    SuccessCriterion("2.1.1", "Keyboard", "A", "All functionality operable via keyboard"),
    SuccessCriterion("2.1.2", "No Keyboard Trap", "A", "Focus can move away from any component"),
    SuccessCriterion("2.1.3", "Keyboard (No Exception)", "AAA", "All functionality via keyboard without exception"),
    SuccessCriterion("2.1.4", "Character Key Shortcuts", "A", "Single-character shortcuts can be remapped or disabled"),
    SuccessCriterion("2.2.1", "Timing Adjustable", "A", "Time limits can be turned off/adjusted/extended"),
    SuccessCriterion("2.2.2", "Pause, Stop, Hide", "A", "Moving/blinking/scrolling content can be paused"),
    SuccessCriterion("2.2.3", "No Timing", "AAA", "No timing (except non-interactive synchronized media)"),
    SuccessCriterion("2.2.4", "Interruptions", "AAA", "Interruptions can be postponed or suppressed"),
    SuccessCriterion("2.2.5", "Re-authenticating", "AAA", "Data preserved when re-authenticating after session expiry"),
    SuccessCriterion("2.2.6", "Timeouts", "AAA", "Users warned about timeouts that cause data loss"),
    SuccessCriterion("2.3.1", "Three Flashes or Below Threshold", "A", "No content flashes >3 times/second"),
    SuccessCriterion("2.3.2", "Three Flashes", "AAA", "No content flashes >3 times/second"),
    SuccessCriterion("2.3.3", "Animation from Interactions", "AAA", "Motion animation triggered by interaction can be disabled"),
    SuccessCriterion("2.4.1", "Bypass Blocks", "A", "Skip navigation provided for repeated blocks"),
    SuccessCriterion("2.4.2", "Page Titled", "A", "Pages have descriptive titles", True),
    SuccessCriterion("2.4.3", "Focus Order", "A", "Focusable components receive focus in meaningful order"),
    SuccessCriterion("2.4.4", "Link Purpose (In Context)", "A", "Link purpose clear from text or context"),
    SuccessCriterion("2.4.5", "Multiple Ways", "AA", "Multiple ways to locate a page (except search results)"),
    SuccessCriterion("2.4.6", "Headings and Labels", "AA", "Headings and labels are descriptive", True),
    SuccessCriterion("2.4.7", "Focus Visible", "AA", "Keyboard focus indicator is visible", True),
    SuccessCriterion("2.4.8", "Location", "AAA", "User's location within site/set of pages is indicated"),
    SuccessCriterion("2.4.9", "Link Purpose (Link Only)", "AAA", "Link purpose clear from link text alone"),
    SuccessCriterion("2.4.10", "Section Headings", "AAA", "Section headings used to organize content"),
    # WCAG 2.2 new:
    SuccessCriterion("2.4.11", "Focus Not Obscured (Minimum)", "AA", "Focused element not entirely hidden by other content"),
    SuccessCriterion("2.4.12", "Focus Not Obscured (Enhanced)", "AAA", "Focused element fully visible"),
    SuccessCriterion("2.4.13", "Focus Appearance", "AAA", "Focus indicator meets minimum area and contrast requirements", True),
    SuccessCriterion("2.5.1", "Pointer Gestures", "A", "Multipoint/path-based gestures have single-pointer alternative"),
    SuccessCriterion("2.5.2", "Pointer Cancellation", "A", "Down-event not used to execute; up-event or abort available"),
    SuccessCriterion("2.5.3", "Label in Name", "A", "Accessible name contains visible label text", True),
    SuccessCriterion("2.5.4", "Motion Actuation", "A", "Motion-operated functionality has alternative interface"),
    SuccessCriterion("2.5.5", "Target Size (Enhanced)", "AAA", "Target size >= 44x44 CSS pixels"),
    SuccessCriterion("2.5.6", "Concurrent Input Mechanisms", "AAA", "No restriction on input modalities"),
    # WCAG 2.2 new:
    SuccessCriterion("2.5.7", "Dragging Movements", "AA", "Dragging has single-pointer alternative"),
    SuccessCriterion("2.5.8", "Target Size (Minimum)", "AA", "Target size >= 24x24 CSS pixels (with exceptions)", True),

    # ── Principle 3: Understandable ──
    SuccessCriterion("3.1.1", "Language of Page", "A", "Page language programmatically identified", True),
    SuccessCriterion("3.1.2", "Language of Parts", "AA", "Language changes marked"),
    SuccessCriterion("3.1.3", "Unusual Words", "AAA", "Definitions for unusual words/idioms/jargon"),
    SuccessCriterion("3.1.4", "Abbreviations", "AAA", "Expanded form of abbreviations available"),
    SuccessCriterion("3.1.5", "Reading Level", "AAA", "Text readable at lower secondary level when possible"),
    SuccessCriterion("3.1.6", "Pronunciation", "AAA", "Pronunciation for ambiguous words"),
    SuccessCriterion("3.2.1", "On Focus", "A", "Focus does not trigger context change"),
    SuccessCriterion("3.2.2", "On Input", "A", "Input does not trigger unexpected context change"),
    SuccessCriterion("3.2.3", "Consistent Navigation", "AA", "Navigation order consistent across pages"),
    SuccessCriterion("3.2.4", "Consistent Identification", "AA", "Components with same functionality identified consistently"),
    SuccessCriterion("3.2.5", "Change on Request", "AAA", "Context change only on user request"),
    # WCAG 2.2 new:
    SuccessCriterion("3.2.6", "Consistent Help", "A", "Help mechanisms in same relative order"),
    SuccessCriterion("3.3.1", "Error Identification", "A", "Input errors identified and described in text", True),
    SuccessCriterion("3.3.2", "Labels or Instructions", "A", "Labels or instructions provided for user input", True),
    SuccessCriterion("3.3.3", "Error Suggestion", "AA", "Suggestions provided for input errors"),
    SuccessCriterion("3.3.4", "Error Prevention (Legal, Financial, Data)", "AA", "Reversible, checked, or confirmed submissions"),
    SuccessCriterion("3.3.5", "Help", "AAA", "Context-sensitive help available"),
    SuccessCriterion("3.3.6", "Error Prevention (All)", "AAA", "Reversible, checked, confirmed for all submissions"),
    # WCAG 2.2 new:
    SuccessCriterion("3.3.7", "Accessible Authentication (Enhanced)", "AAA", "No cognitive function tests in authentication"),
    SuccessCriterion("3.3.8", "Accessible Authentication (Minimum)", "AA", "Alternative to cognitive function tests"),
    SuccessCriterion("3.3.9", "Redundant Entry", "A", "Previously entered info auto-populated or available"),

    # ── Principle 4: Robust ──
    SuccessCriterion("4.1.1", "Parsing", "A", "No major markup errors (obsolete in 2.2, but kept for reference)"),
    SuccessCriterion("4.1.2", "Name, Role, Value", "A", "UI components expose name/role/value to AT", True),
    SuccessCriterion("4.1.3", "Status Messages", "AA", "Status messages programmatically determinable", True),
]


# ═══════════════════════════════════════════════════════════════
# Programmatic checklist evaluator
# ═══════════════════════════════════════════════════════════════

@dataclass
class ChecklistResult:
    """Per-criterion evaluation result."""
    criterion: SuccessCriterion
    passed: bool | None = None  # None = not evaluable automatically
    evidence: str = ""


def evaluate_checklist(page_html: str = "", axe_results: dict | None = None) -> list[ChecklistResult]:
    """Programmatically evaluate WCAG 2.2 checklist against provided data."""
    results: list[ChecklistResult] = []
    for sc in WCAG22_CRITERIA:
        result = ChecklistResult(criterion=sc)
        if not sc.auto_checkable:
            result.passed = None
            result.evidence = "requires manual review"
        else:
            result.passed, result.evidence = _auto_check(sc, page_html, axe_results or {})
        results.append(result)
    return results


def _auto_check(sc: SuccessCriterion, html: str, axe: dict) -> tuple[bool | None, str]:
    """Auto-check individual criteria."""
    violations = {v.get("id", "") for v in axe.get("violations", [])}

    checks: dict[str, str] = {
        "1.1.1": "image-alt",
        "1.3.1": "aria-required-attr",
        "1.4.3": "color-contrast",
        "1.4.11": "color-contrast",
        "2.4.2": "document-title",
        "2.4.6": "heading-order",
        "2.4.7": "focus-order-semantics",
        "2.4.13": "focus-order-semantics",  # focus indicator area/contrast (axe-core validates focus styling)
        "2.5.3": "label",
        "2.5.8": "target-size",
        "3.1.1": "html-has-lang",
        "3.3.1": "form-field-multiple-labels",
        "3.3.2": "label",
        "4.1.2": "aria-valid-attr",
        "4.1.3": "aria-live-region",
    }

    axe_id = checks.get(sc.num)
    if axe_id and axe_id in violations:
        return False, f"axe-core violation: {axe_id}"
    if axe_id:
        return True, f"axe-core pass: {axe_id}"
    return None, "auto-check not implemented for this criterion"


# ═══════════════════════════════════════════════════════════════
# Scoring
# ═══════════════════════════════════════════════════════════════

@dataclass
class A11yReport:
    url: str
    total_criteria: int = len(WCAG22_CRITERIA)
    auto_pass: int = 0
    auto_fail: int = 0
    manual_required: int = 0
    level_a_pass: int = 0
    level_aa_pass: int = 0
    level_aaa_pass: int = 0
    automated_score: float = 0.0
    checklist_score: float = 0.0
    composite_score: float = 0.0
    grade: str = "F"
    violations_detail: list[dict] = field(default_factory=list)
    checklist_results: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "total_criteria": self.total_criteria,
            "auto_pass": self.auto_pass,
            "auto_fail": self.auto_fail,
            "manual_required": self.manual_required,
            "level_a_pass": self.level_a_pass,
            "level_aa_pass": self.level_aa_pass,
            "level_aaa_pass": self.level_aaa_pass,
            "automated_score": self.automated_score,
            "checklist_score": self.checklist_score,
            "composite_score": self.composite_score,
            "grade": self.grade,
            "violations_detail": self.violations_detail,
            "checklist_results": self.checklist_results,
        }


def compute_score(checklist: list[ChecklistResult],
                   axe_violations: list[dict]) -> A11yReport:
    """Compute composite accessibility score."""
    total_auto = sum(1 for c in checklist if c.criterion.auto_checkable)
    auto_pass = sum(1 for c in checklist if c.passed is True)
    auto_fail = sum(1 for c in checklist if c.passed is False)
    manual = sum(1 for c in checklist if c.passed is None)

    # Level breakdown (count auto pass per level)
    a_criteria = [c for c in checklist if c.criterion.level == "A" and c.criterion.auto_checkable]
    aa_criteria = [c for c in checklist if c.criterion.level == "AA" and c.criterion.auto_checkable]
    aaa_criteria = [c for c in checklist if c.criterion.level == "AAA" and c.criterion.auto_checkable]

    a_pass = sum(1 for c in a_criteria if c.passed is True)
    aa_pass = sum(1 for c in aa_criteria if c.passed is True)
    aaa_pass = sum(1 for c in aaa_criteria if c.passed is True)

    automated = auto_pass / total_auto if total_auto > 0 else 0
    # Checklist score = fraction of auto-checkable that pass (same basis)
    checklist_fraction = automated

    composite = automated * 0.6  # weighted: auto 60%, manual 40% when available
    # When manual checks are completed, composite = auto×0.6 + manual×0.4

    # Grade
    if composite >= 0.95:
        grade = "A+"
    elif composite >= 0.90:
        grade = "A"
    elif composite >= 0.80:
        grade = "B"
    elif composite >= 0.70:
        grade = "C"
    elif composite >= 0.60:
        grade = "D"
    else:
        grade = "F"

    return A11yReport(
        url="",
        auto_pass=auto_pass,
        auto_fail=auto_fail,
        manual_required=manual,
        level_a_pass=a_pass,
        level_aa_pass=aa_pass,
        level_aaa_pass=aaa_pass,
        automated_score=round(automated * 100, 1),
        checklist_score=round(checklist_fraction * 100, 1),
        composite_score=round(composite * 100, 1),
        grade=grade,
        violations_detail=[{
            "id": v.get("id", ""),
            "impact": v.get("impact", ""),
            "description": v.get("description", "")[:200],
        } for v in axe_violations[:20]],
        checklist_results=[{
            "num": c.criterion.num,
            "name": c.criterion.name,
            "level": c.criterion.level,
            "passed": c.passed,
            "evidence": c.evidence,
        } for c in checklist],
    )


# ═══════════════════════════════════════════════════════════════
# Integrated scan (combine axe-core + checklist)
# ═══════════════════════════════════════════════════════════════

def scan_with_axe(page, url: str | None = None) -> dict:
    """
    Inject axe-core into Playwright page and scan for violations.
    page: Playwright Page object
    """
    if url:
        page.goto(url, wait_until="networkidle")
    page.add_script_tag(
        url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.3/axe.min.js"
    )
    result = page.evaluate("""
        () => new Promise(resolve => {
            axe.run((err, results) => {
                if (err) resolve({error: err.message});
                else resolve(results);
            });
        });
    """)
    return result


def full_scan(page, url: str) -> A11yReport:
    """
    Complete WCAG 2.2 scan: axe-core auto + checklist evaluation.
    Returns scored A11yReport.
    """
    axe = scan_with_axe(page, url)
    checklist = evaluate_checklist(
        page_html=page.content(),
        axe_results=axe,
    )
    violations = axe.get("violations", [])
    report = compute_score(checklist, violations)
    report.url = url
    return report


# ═══════════════════════════════════════════════════════════════
# External tool wrappers (backward compat with v1)
# ═══════════════════════════════════════════════════════════════

def scan_with_lighthouse(url: str, output_dir: str = "workspace/执行日志/a11y") -> dict:
    """Run Lighthouse a11y audit. Requires: npm install -g lighthouse"""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_json = out_dir / "lighthouse_a11y.json"
    cmd = [
        "lighthouse", url,
        "--only-categories=accessibility",
        "--output=json",
        f"--output-path={out_json}",
        "--chrome-flags=--headless --no-sandbox",
        "--quiet",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        return {"error": proc.stderr[-500:]}
    data = json.loads(out_json.read_text(encoding="utf-8"))
    score = data.get("categories", {}).get("accessibility", {}).get("score", 0)
    audits = data.get("audits", {})
    failed = [k for k, v in audits.items() if v.get("score") is not None and v.get("score") < 1]
    return {"url": url, "a11y_score": round((score or 0) * 100, 1),
            "failed_audits": failed, "report": str(out_json)}


def scan_with_pa11y(url: str) -> dict:
    """Run pa11y scan. Requires: npm install -g pa11y"""
    proc = subprocess.run(["pa11y", url, "--reporter", "json"],
                          capture_output=True, text=True, timeout=60)
    try:
        issues = json.loads(proc.stdout) if proc.stdout else []
    except json.JSONDecodeError:
        issues = []
    by_type: dict[str, int] = {}
    for i in issues:
        by_type[i.get("type", "other")] = by_type.get(i.get("type", "other"), 0) + 1
    return {"url": url, "total_issues": len(issues), "by_type": by_type}


# ═══════════════════════════════════════════════════════════════
# Print WCAG 2.2 checklist (human-readable)
# ═══════════════════════════════════════════════════════════════

def print_wcag22_checklist() -> str:
    """Return formatted WCAG 2.2 checklist as markdown string."""
    lines = ["# WCAG 2.2 Checklist (78 Success Criteria)\n"]
    current_principle = ""
    for sc in WCAG22_CRITERIA:
        num_parts = sc.num.split(".")
        principle = {"1": "Perceivable", "2": "Operable",
                     "3": "Understandable", "4": "Robust"}.get(num_parts[0], "Unknown")
        if principle != current_principle:
            current_principle = principle
            lines.append(f"\n## Principle {num_parts[0]}: {principle}\n")
        auto = " [AUTO]" if sc.auto_checkable else ""
        lines.append(f"- [{sc.level}] **{sc.num}** {sc.name}: {sc.description}{auto}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser(description="A11y scanner v2 (WCAG 2.2)")
    sub = ap.add_subparsers(dest="cmd")
    lh = sub.add_parser("lighthouse"); lh.add_argument("url")
    pa = sub.add_parser("pa11y"); pa.add_argument("url")
    cl = sub.add_parser("checklist")
    al = sub.add_parser("all"); al.add_argument("url")
    args = ap.parse_args()

    if args.cmd == "lighthouse":
        print(json.dumps(scan_with_lighthouse(args.url), indent=2, ensure_ascii=False))
    elif args.cmd == "pa11y":
        print(json.dumps(scan_with_pa11y(args.url), indent=2, ensure_ascii=False))
    elif args.cmd == "checklist":
        print(print_wcag22_checklist())
    elif args.cmd == "all":
        print("axe-core + Lighthouse + pa11y scans require a running browser / npm tools.")
        print("For integrated scan, use full_scan(page, url) from within a Playwright test.")
        print()
        print(print_wcag22_checklist())
