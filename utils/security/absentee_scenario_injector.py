# SPDX-License-Identifier: MIT
"""
Absentee Scenario Injector — 缺席者场景注入 (Phase 3.3).

Force-injects edge user scenarios that scripted testing typically overlooks:
disability, elderly, minor, offline, mental crisis, non-native speakers.

Integrates with:
  - a11y_scanner.py (WCAG 2.1 compliance verification)
  - i18n_checker.py  (RTL layout, cultural taboos, translation quality)
  - testcase-designer expert (exploratory charters, scenario templates)

Referenced by: 03-用例设计 expert + 02-coverage-matrix Phase 3.3.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from utils.paths import get_output_dir

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Scenario definitions — canonical absentee groups
# ═══════════════════════════════════════════════════════════════

@dataclass
class Scenario:
    id: str
    group: str                # absentee group
    severity: str             # "P0" | "P1" | "P2"
    title: str
    description: str
    test_steps: list[str]
    expected: str
    wcag_refs: list[str] = field(default_factory=list)  # WCAG 2.1 SC refs
    i18n_tags: list[str] = field(default_factory=list)   # RTL, locale, cultural
    tags: list[str] = field(default_factory=list)


# Canonical absentee groups
ABSENTEE_GROUPS = {
    "visual_impairment": {
        "label": "视觉障碍",
        "description": "Screen reader, color blindness, low vision, blindness",
        "p0_count": 3, "p1_count": 4, "p2_count": 2,
    },
    "motor_impairment": {
        "label": "运动障碍",
        "description": "Keyboard-only, switch device, voice control, tremor",
        "p0_count": 2, "p1_count": 3, "p2_count": 2,
    },
    "hearing_impairment": {
        "label": "听觉障碍",
        "description": "Captions, transcripts, visual-only alerts",
        "p0_count": 2, "p1_count": 2, "p2_count": 2,
    },
    "cognitive_impairment": {
        "label": "认知障碍",
        "description": "Simple language, consistent nav, error recovery, dyslexia",
        "p0_count": 2, "p1_count": 3, "p2_count": 2,
    },
    "elderly": {
        "label": "老年用户",
        "description": "Large touch targets, high contrast, simplified flows, font scaling",
        "p0_count": 2, "p1_count": 3, "p2_count": 2,
    },
    "minor": {
        "label": "未成年用户",
        "description": "Age-gating, COPPA/GDPR-K, content filtering, parental consent",
        "p0_count": 2, "p1_count": 2, "p2_count": 2,
    },
    "offline_low_bandwidth": {
        "label": "离线/弱网",
        "description": "Offline-first, sync conflicts, data loss prevention, 2G fallback",
        "p0_count": 2, "p1_count": 3, "p2_count": 2,
    },
    "mental_crisis": {
        "label": "精神危机状态",
        "description": "Suicide/self-harm content detection, crisis resource routing, de-escalation UX",
        "p0_count": 3, "p1_count": 2, "p2_count": 2,
    },
    "non_native_speaker": {
        "label": "非母语用户",
        "description": "Translation quality, RTL layout, cultural context, regional formats",
        "p0_count": 1, "p1_count": 3, "p2_count": 2,
    },
}


# ═══════════════════════════════════════════════════════════════
# Scenario library
# ═══════════════════════════════════════════════════════════════

SCENARIOS: list[Scenario] = [
    # ── Visual impairment ──
    Scenario("VI-001", "visual_impairment", "P0",
        "Screen reader navigates full user journey",
        "Verify all interactive elements have accessible names, landmarks are structured, and form errors are announced by screen reader.",
        ["Launch screen reader (NVDA/VoiceOver/TalkBack)", "Navigate to login page", "Tab through all form fields — verify each announces label + state",
         "Submit empty form — verify error message is read aloud", "Complete login — verify success announcement",
         "Navigate main dashboard — verify landmark roles (banner/main/navigation)"],
        "All interactive elements reachable and announced. Error messages read on appearance. Landmarks correctly identified.",
        wcag_refs=["1.1.1", "1.3.1", "4.1.2", "4.1.3"],
        tags=["screen-reader", "aria", "landmarks", "forms"]),
    Scenario("VI-002", "visual_impairment", "P0",
        "Color blindness does not block critical information",
        "Verify no information is conveyed by color alone. Status indicators use icons+text, not just red/green.",
        ["Enable deuteranopia simulation (Chrome DevTools Rendering tab)", "Navigate to status dashboard",
         "Check all status badges — verify each has text label (not just color dot)",
         "Check charts — verify patterns or labels distinguish data series",
         "Check form validation — verify error fields have icon + border + text, not just red border"],
        "All status, validation, and chart information distinguishable without color perception.",
        wcag_refs=["1.4.1"],
        tags=["color-blindness", "deuteranopia", "charts", "validation"]),
    Scenario("VI-003", "visual_impairment", "P0",
        "200% zoom does not break layout or hide content",
        "Verify page is usable at 200% browser zoom with no horizontal scroll or overlapping content.",
        ["Set browser zoom to 200%", "Navigate through all primary pages (login→dashboard→settings→logout)",
         "Check no content is clipped or hidden", "Check no horizontal scrollbar appears",
         "Verify all CTAs remain clickable"],
        "All content visible and functional at 200% zoom. No horizontal scroll.",
        wcag_refs=["1.4.4"],
        tags=["zoom", "responsive", "reflow"]),

    # ── Motor impairment ──
    Scenario("MI-001", "motor_impairment", "P0",
        "Full keyboard navigation (no mouse)",
        "Verify all functionality is operable via keyboard alone with visible focus indicators.",
        ["Disconnect mouse", "Tab through entire page — verify focus ring is visible on every interactive element",
         "Verify focus order matches visual layout", "Use Enter/Space to activate buttons and links",
         "Use Escape to close modals/dropdowns", "Verify no keyboard traps (Tab never gets stuck)"],
        "All functionality reachable and operable via keyboard. Visible focus indicator on every element.",
        wcag_refs=["2.1.1", "2.1.2", "2.4.3", "2.4.7"],
        tags=["keyboard", "focus", "tab-order"]),
    Scenario("MI-002", "motor_impairment", "P0",
        "Touch targets meet minimum size (44×44 CSS px)",
        "Verify all interactive elements have sufficient touch target size per WCAG 2.5.5.",
        ["Open page on mobile viewport (375px)", "Identify all tappable elements (buttons, links, inputs)",
         "Measure each target — verify ≥44×44 CSS px or has sufficient spacing",
         "Check adjacent targets don't overlap", "Test with fat-finger simulation (34px offset)"],
        "All touch targets ≥44×44px or have adequate spacing from neighbors.",
        wcag_refs=["2.5.5", "2.5.8"],
        tags=["touch-target", "mobile", "motor"]),

    # ── Hearing impairment ──
    Scenario("HI-001", "hearing_impairment", "P0",
        "All video/audio content has captions or transcripts",
        "Verify prerecorded media has synchronized captions and audio-only content has transcripts.",
        ["Identify all <video> and <audio> elements", "Check <track> elements exist for captions",
         "Play video — verify captions are synchronized", "Verify captions include speaker identification and sound effects",
         "For audio-only (podcasts), verify transcript link is present and complete"],
        "All video has captions. All audio has transcripts. Captions include non-speech sounds.",
        wcag_refs=["1.2.2", "1.2.3", "1.2.5"],
        tags=["captions", "transcript", "video", "audio"]),

    # ── Cognitive impairment ──
    Scenario("CI-001", "cognitive_impairment", "P0",
        "Error messages are clear and provide recovery guidance",
        "Verify error messages use plain language, explain what went wrong, and how to fix it.",
        ["Trigger validation errors on every form (empty submit, invalid email, weak password)",
         "Check each error message: is it in plain language? Does it explain the problem?",
         "Does it tell the user how to fix it? (e.g. 'Password needs 8+ characters, including a number')",
         "Check error stays visible until corrected", "Check success confirmation is clear"],
        "Every error message: (1) identifies the problem, (2) explains in plain language, (3) provides fix guidance.",
        wcag_refs=["3.3.1", "3.3.2", "3.3.3"],
        tags=["error-messages", "plain-language", "forms"]),
    Scenario("CI-002", "cognitive_impairment", "P0",
        "Session timeout with data preservation warning",
        "Verify session expiry warns user and preserves unsaved data, with option to extend.",
        ["Start filling a multi-step form", "Wait for session timeout period (or force via DevTools)",
         "Verify warning appears before timeout (e.g. 'Your session expires in 2 minutes')",
         "Verify 'Extend session' button works", "Let session expire — verify unsaved data is preserved",
         "After re-login, verify form state is restored"],
        "Timeout warning displayed ≥2 min before expiry. Data preserved. Re-login restores state.",
        wcag_refs=["2.2.1", "2.2.5"],
        tags=["timeout", "data-preservation", "session"]),

    # ── Elderly ──
    Scenario("EL-001", "elderly", "P0",
        "Font scaling to 200% via browser settings",
        "Verify all text scales proportionally when browser default font size is set to 32px.",
        ["Set browser default font size to 32px (Chrome: Settings→Appearance→Font size→Very large)",
         "Navigate through all primary pages", "Verify no text is clipped, overlapped, or hidden",
         "Verify buttons and containers grow to accommodate larger text",
         "Verify line height keeps text readable (no crowding)"],
        "All text visible and readable at 32px base font size. Containers adapt to content.",
        wcag_refs=["1.4.4", "1.4.12"],
        tags=["font-scaling", "elderly", "text-resize"]),

    # ── Minor ──
    Scenario("MN-001", "minor", "P0",
        "Age gate prevents underage access to age-restricted content",
        "Verify age verification gate appears before age-restricted content and cannot be trivially bypassed.",
        ["Visit age-restricted page without age verification cookie", "Verify age gate appears before content",
         "Enter underage birth date — verify access is blocked", "Try to bypass via URL manipulation — verify gate re-checks",
         "Check that gate uses server-side validation (not just client-side JS)", "Verify COPPA/GDPR-K consent flow for 13-16 age range"],
        "Age gate blocks underage access server-side. Cannot bypass via URL or cookie manipulation.",
        wcag_refs=[],
        tags=["age-gate", "coppa", "gdpr-k", "minor"]),

    # ── Offline / Low bandwidth ──
    Scenario("OF-001", "offline_low_bandwidth", "P0",
        "App functions offline with graceful degradation",
        "Verify core features work offline and data syncs correctly when connectivity returns.",
        ["Load app with network connected (warm cache)", "Enable offline mode (DevTools→Network→Offline)",
         "Navigate core pages — verify cached content displays", "Perform action (e.g. save draft) — verify queued locally",
         "Restore connectivity — verify queued actions sync successfully",
         "Check conflict resolution when remote data changed during offline"],
        "Core pages display cached content. Actions queued offline. Sync on reconnect. Conflicts flagged.",
        tags=["offline", "service-worker", "sync", "cache"]),
    Scenario("OF-002", "offline_low_bandwidth", "P0",
        "App degrades gracefully on slow 2G connection",
        "Verify app loads and is usable on 2G throttled connection without timeout errors.",
        ["Set network throttle to 'Slow 2G' (DevTools→Network→Throttling)",
         "Load app — verify it loads within 30 seconds", "Verify loading indicators display (not blank screen)",
         "Navigate through pages — verify each loads with progress feedback",
         "Submit a form — verify it succeeds (no timeout)", "Check image lazy-loading works"],
        "App loads on 2G within 30s. Progress indicators shown. Forms submit without timeout. Images lazy-load.",
        tags=["2g", "slow-network", "progressive-loading", "timeout"]),

    # ── Mental crisis ──
    Scenario("MC-001", "mental_crisis", "P0",
        "Self-harm content detection with crisis resource routing",
        "Verify the app detects self-harm/ suicidal content and routes user to crisis resources, not punitive actions.",
        ["Submit content containing self-harm keywords (in test environment)", "Verify response is empathetic, not punitive",
         "Verify crisis hotline/resource is offered (not just content removal)", "Verify user is not banned/penalized for crisis content",
         "Check that detection works across input surfaces (posts, messages, search)",
         "Verify human review escalation path exists"],
        "Self-harm content detected. Crisis resources offered (hotline number + link). No punitive action taken.",
        tags=["self-harm", "crisis", "suicide-prevention", "content-moderation", "safety"]),
    Scenario("MC-002", "mental_crisis", "P0",
        "Distressed user UX: de-escalation patterns",
        "Verify UI patterns that de-escalate distressed users: no countdown timers, no aggressive urgency, clear exit paths.",
        ["Review all time-limited flows (checkout, booking, verification)", "Verify no aggressive countdown timers (< 5 min visible)",
         "Verify cancel/exit is always visible and one-click", "Verify no dark patterns (confirm-shaming, hidden costs, forced continuity)",
         "Check support contact is findable in < 2 clicks from any page"],
        "No aggressive timers. Exit always one-click. No dark patterns. Support always accessible.",
        tags=["de-escalation", "ux", "dark-patterns", "support"]),
    Scenario("MC-003", "mental_crisis", "P0",
        "Content warning gates for potentially triggering material",
        "Verify content warnings precede potentially triggering material with opt-in to view.",
        ["Identify pages with potentially triggering content (violence, self-harm discussion, graphic medical)",
         "Verify interstitial warning appears before content loads", "Verify user must explicitly opt-in (not just scroll past)",
         "Verify 'skip/back' option is equally prominent", "Check that preference is remembered (don't re-warn every visit)"],
        "Trigger warnings appear before sensitive content. User must opt-in. Skip is equally easy. Preference remembered.",
        tags=["content-warning", "trigger", "opt-in", "trauma-informed"]),

    # ── Non-native speaker ──
    Scenario("NN-001", "non_native_speaker", "P0",
        "RTL layout renders correctly for Arabic/Hebrew",
        "Verify all pages render correctly in RTL mode with no layout breakage.",
        ["Switch app language to Arabic (ar)", "Navigate all primary pages",
         "Verify text aligns right, UI elements mirror (back button on right, etc.)",
         "Verify numbers and embedded LTR text (URLs, code) remain LTR within RTL flow",
         "Check forms: labels right-aligned, inputs right-aligned", "Switch back to LTR — verify no corruption"],
        "RTL layout: text right-aligned, UI mirrored, embedded LTR preserved. No layout breakage.",
        i18n_tags=["RTL", "ar", "he"],
        tags=["rtl", "arabic", "hebrew", "layout"]),
]


# ═══════════════════════════════════════════════════════════════
# Scenario query / injection API
# ═══════════════════════════════════════════════════════════════

def list_groups() -> list[dict]:
    """Return all absentee groups with scenario counts."""
    result = []
    for key, info in ABSENTEE_GROUPS.items():
        count = sum(1 for s in SCENARIOS if s.group == key)
        result.append({
            "id": key,
            "label": info["label"],
            "description": info["description"],
            "scenario_count": count,
        })
    return result


def query_scenarios(
    groups: list[str] | None = None,
    severity: str | None = None,
    tags: list[str] | None = None,
) -> list[Scenario]:
    """Query scenarios by group, severity, and/or tags."""
    results = SCENARIOS
    if groups:
        results = [s for s in results if s.group in groups]
    if severity:
        results = [s for s in results if s.severity == severity]
    if tags:
        results = [s for s in results if any(t in s.tags for t in tags)]
    return results


def inject_scenarios(
    groups: list[str] | None = None,
    min_severity: str = "P2",
    count: int | None = None,
) -> list[dict]:
    """
    Inject absentee scenarios into test plan.
    Returns list of scenario dicts ready for testcase-designer consumption.
    """
    severity_order = {"P0": 0, "P1": 1, "P2": 2}
    candidates = query_scenarios(groups=groups)
    candidates = [s for s in candidates
                  if severity_order.get(s.severity, 99) <= severity_order.get(min_severity, 99)]
    candidates.sort(key=lambda s: severity_order.get(s.severity, 99))

    if count:
        candidates = candidates[:count]

    return [_scenario_to_dict(s) for s in candidates]


def _scenario_to_dict(s: Scenario) -> dict:
    return {
        "id": s.id,
        "group": s.group,
        "group_label": ABSENTEE_GROUPS.get(s.group, {}).get("label", s.group),
        "severity": s.severity,
        "title": s.title,
        "description": s.description,
        "test_steps": s.test_steps,
        "expected": s.expected,
        "wcag_refs": s.wcag_refs,
        "i18n_tags": s.i18n_tags,
        "tags": s.tags,
    }


# ═══════════════════════════════════════════════════════════════
# Charter generation for testcase-designer
# ═══════════════════════════════════════════════════════════════

def generate_charter(scenario: Scenario, module: str = "", duration_min: int = 30) -> str:
    """Generate an SBTM charter markdown for a specific scenario."""
    lines = [
        f"# Charter: {scenario.title}",
        "## 范围",
        f"- 缺席者组: {ABSENTEE_GROUPS.get(scenario.group, {}).get('label', scenario.group)}",
        f"- 场景ID: {scenario.id}",
        f"- 严重性: {scenario.severity}",
        f"- 时长: {duration_min} min",
    ]
    if module:
        lines.append(f"- 模块: {module}")
    lines.extend([
        f"- WCAG: {', '.join(scenario.wcag_refs)}" if scenario.wcag_refs else "",
        f"- i18n: {', '.join(scenario.i18n_tags)}" if scenario.i18n_tags else "",
        "",
        "## 描述",
        scenario.description,
        "",
        "## 测试步骤",
    ])
    for i, step in enumerate(scenario.test_steps, 1):
        lines.append(f"{i}. {step}")
    lines.extend([
        "",
        "## 预期结果",
        scenario.expected,
        "",
        "## 发现 (Session中记录)",
        "- Bug:",
        "- 疑问:",
        "- 待跟进:",
    ])
    return "\n".join(line for line in lines if line != "")


def generate_batch_charters(
    groups: list[str] | None = None,
    severity: str = "P0",
    output_dir: str = "workspace/测试用例/absentee",
    module: str = "",
) -> list[str]:
    """Generate SBTM charters for all matching scenarios and write to files."""
    scenarios = query_scenarios(groups=groups, severity=severity)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    paths = []
    for s in scenarios:
        charter_md = generate_charter(s, module=module)
        filename = f"charter_{s.id}_{s.group}.md"
        path = Path(output_dir) / filename
        path.write_text(charter_md, encoding="utf-8")
        paths.append(str(path))
    logger.info("Generated %d absentee charters → %s", len(paths), output_dir)
    return paths


# ═══════════════════════════════════════════════════════════════
# Coverage report
# ═══════════════════════════════════════════════════════════════

def coverage_report(injected_scenarios: list[dict] | None = None) -> dict:
    """Generate coverage summary: which absentee groups are covered."""
    if injected_scenarios is None:
        injected_scenarios = inject_scenarios()

    covered_groups: dict[str, int] = {}
    for s in injected_scenarios:
        g = s["group"]
        covered_groups[g] = covered_groups.get(g, 0) + 1

    total_groups = len(ABSENTEE_GROUPS)
    covered_count = len(covered_groups)
    total_scenarios = len(injected_scenarios)

    missing = [g for g in ABSENTEE_GROUPS if g not in covered_groups]

    return {
        "total_absentee_groups": total_groups,
        "groups_covered": covered_count,
        "groups_missing": missing,
        "coverage_pct": round(covered_count / total_groups * 100, 1),
        "total_scenarios_injected": total_scenarios,
        "per_group": covered_groups,
        "recommendation": (
            f"Covered {covered_count}/{total_groups} absentee groups "
            f"({covered_count/total_groups:.0%})."
            + (f" Missing: {', '.join(missing)}." if missing else " All groups covered.")
        ),
    }


# ═══════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════

def export_injection_plan(
    scenarios: list[dict],
    output_dir: str = None,
) -> str:
    """Export the absentee scenario injection plan as JSON."""
    if output_dir is None:
        output_dir = str(get_output_dir("absentee-scenarios"))
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output_dir) / f"absentee_plan_{ts}.json"

    data = {
        "generated_at": datetime.now().isoformat(),
        "total_scenarios": len(scenarios),
        "coverage": coverage_report(scenarios),
        "scenarios": scenarios,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Absentee injection plan → %s (%d scenarios)", path, len(scenarios))
    return str(path)


def ci_summary(scenarios: list[dict]) -> str:
    """One-line CI-friendly summary."""
    cov = coverage_report(scenarios)
    lines = [
        f" Absentee Scenario Injection: {cov['total_scenarios_injected']} scenarios "
        f"across {cov['groups_covered']}/{cov['total_absentee_groups']} groups "
        f"({cov['coverage_pct']}%)",
    ]
    if cov["groups_missing"]:
        lines.append(f"   Missing groups: {', '.join(cov['groups_missing'])}")
    for g, count in sorted(cov["per_group"].items()):
        label = ABSENTEE_GROUPS.get(g, {}).get("label", g)
        lines.append(f"   {label}: {count} scenarios")
    return "\n".join(lines)
