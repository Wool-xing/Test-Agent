# SPDX-License-Identifier: MIT
"""Unit tests for taboo_matrix.py — Phase 5 禁忌矩阵数据完整性."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_utils_dir = Path(__file__).resolve().parents[2] / "utils"
if str(_utils_dir) not in sys.path:
    sys.path.insert(0, str(_utils_dir))

from taboo_matrix import (
    Severity,
    TabooCategory,
    TABOO_WORDS,
    TABOO_COLORS,
    TABOO_NUMBERS,
    TABOO_HOLIDAYS,
    SACRED_CONTEXTS,
    get_taboo_words,
    get_taboo_colors,
    get_taboo_numbers,
    get_taboo_holidays,
    get_sacred_contexts,
    get_supported_locales,
    get_matrix_summary,
)


# ═══════════════════════════════════════════════════════════════
# Data integrity
# ═══════════════════════════════════════════════════════════════

class TestDataIntegrity:
    """All five data tables must be non-empty and well-formed."""

    def test_taboo_words_not_empty(self):
        assert len(TABOO_WORDS) >= 40, "Should have 40+ taboo words"

    def test_taboo_colors_not_empty(self):
        assert len(TABOO_COLORS) >= 15, "Should have 15+ taboo colors"

    def test_taboo_numbers_not_empty(self):
        assert len(TABOO_NUMBERS) >= 15, "Should have 15+ taboo numbers"

    def test_taboo_holidays_not_empty(self):
        assert len(TABOO_HOLIDAYS) >= 20, "Should have 20+ taboo holiday periods"

    def test_sacred_contexts_not_empty(self):
        assert len(SACRED_CONTEXTS) >= 10, "Should have 10+ sacred context rules"

    def test_every_entry_has_required_fields(self):
        for source, name in [
            (TABOO_WORDS, "TABOO_WORDS"),
            (TABOO_COLORS, "TABOO_COLORS"),
            (TABOO_NUMBERS, "TABOO_NUMBERS"),
            (TABOO_HOLIDAYS, "TABOO_HOLIDAYS"),
        ]:
            for i, entry in enumerate(source):
                assert "locale" in entry, f"{name}[{i}] missing locale"
                assert "severity" in entry, f"{name}[{i}] missing severity"
                assert "reason" in entry, f"{name}[{i}] missing reason"

    def test_no_empty_reason_strings(self):
        for source, name in [
            (TABOO_WORDS, "TABOO_WORDS"),
            (TABOO_COLORS, "TABOO_COLORS"),
            (TABOO_NUMBERS, "TABOO_NUMBERS"),
            (TABOO_HOLIDAYS, "TABOO_HOLIDAYS"),
            (SACRED_CONTEXTS, "SACRED_CONTEXTS"),
        ]:
            for i, entry in enumerate(source):
                assert len(entry.get("reason", "")) >= 5, f"{name}[{i}] reason too short"

    def test_all_severities_valid(self):
        valid = {"critical", "high", "medium"}
        for source, name in [
            (TABOO_WORDS, "TABOO_WORDS"),
            (TABOO_COLORS, "TABOO_COLORS"),
            (TABOO_NUMBERS, "TABOO_NUMBERS"),
            (TABOO_HOLIDAYS, "TABOO_HOLIDAYS"),
            (SACRED_CONTEXTS, "SACRED_CONTEXTS"),
        ]:
            for i, entry in enumerate(source):
                assert entry["severity"] in valid, f"{name}[{i}] severity={entry['severity']} not valid"


# ═══════════════════════════════════════════════════════════════
# Locale coverage
# ═══════════════════════════════════════════════════════════════

class TestLocaleCoverage:
    """Must cover major world locales."""

    def test_supported_locales(self):
        locales = get_supported_locales()
        assert len(locales) >= 14, f"Should cover 14+ locales, got {len(locales)}"
        # Key locales must be present
        assert "zh-CN" in locales
        assert "ja-JP" in locales
        assert "ar-SA" in locales
        assert "en-US" in locales
        assert "hi-IN" in locales

    def test_every_taboo_word_has_known_locale(self):
        known = set(get_supported_locales())
        for entry in TABOO_WORDS:
            assert entry["locale"] in known, f"Unknown locale {entry['locale']} in TABOO_WORDS"

    def test_every_taboo_color_has_known_locale(self):
        known = set(get_supported_locales())
        for entry in TABOO_COLORS:
            assert entry["locale"] in known, f"Unknown locale {entry['locale']} in TABOO_COLORS"

    def test_every_taboo_number_has_known_locale(self):
        known = set(get_supported_locales())
        for entry in TABOO_NUMBERS:
            assert entry["locale"] in known, f"Unknown locale {entry['locale']} in TABOO_NUMBERS"


# ═══════════════════════════════════════════════════════════════
# Query helpers
# ═══════════════════════════════════════════════════════════════

class TestQueryHelpers:
    """get_* functions filter or return all."""

    def test_get_taboo_words_all(self):
        all_words = get_taboo_words()
        assert len(all_words) == len(TABOO_WORDS)

    def test_get_taboo_words_filtered(self):
        zh_words = get_taboo_words("zh-CN")
        assert all(w["locale"] == "zh-CN" for w in zh_words)
        assert len(zh_words) >= 5

    def test_get_taboo_words_unknown_locale_returns_empty(self):
        assert get_taboo_words("xx-XX") == []

    def test_get_taboo_colors_filtered(self):
        ja_colors = get_taboo_colors("ja-JP")
        assert all(c["locale"] == "ja-JP" for c in ja_colors)

    def test_get_taboo_numbers_filtered(self):
        zh_numbers = get_taboo_numbers("zh-CN")
        assert len(zh_numbers) >= 3  # 4, 8, 7, 14, 0
        assert any(n["number"] == 4 for n in zh_numbers)

    def test_get_taboo_holidays_filtered(self):
        us_holidays = get_taboo_holidays("en-US")
        assert any("9月11日" in h["period"] or "Memorial" in h["period"] for h in us_holidays)

    def test_get_sacred_contexts_global(self):
        global_rules = get_sacred_contexts("*")
        assert len(global_rules) >= 5  # global rules are locale="*"
        # Should include global entries
        assert any("儿童用户" in s["context"] for s in global_rules)

    def test_get_sacred_contexts_locale_specific(self):
        zh_rules = get_sacred_contexts("zh-CN")
        # Should include both global (*) and zh-CN entries
        assert any("天安门" in s["context"] for s in zh_rules)


# ═══════════════════════════════════════════════════════════════
# Matrix summary
# ═══════════════════════════════════════════════════════════════

class TestMatrixSummary:
    """get_matrix_summary returns consistent statistics."""

    def test_summary_counts_match_sources(self):
        summary = get_matrix_summary()
        assert summary["taboo_words"] == len(TABOO_WORDS)
        assert summary["taboo_colors"] == len(TABOO_COLORS)
        assert summary["taboo_numbers"] == len(TABOO_NUMBERS)
        assert summary["taboo_holidays"] == len(TABOO_HOLIDAYS)
        assert summary["sacred_contexts"] == len(SACRED_CONTEXTS)
        assert summary["total_entries"] == (
            len(TABOO_WORDS) + len(TABOO_COLORS) + len(TABOO_NUMBERS) +
            len(TABOO_HOLIDAYS) + len(SACRED_CONTEXTS)
        )

    def test_locales_covered_positive(self):
        summary = get_matrix_summary()
        assert summary["locales_covered"] >= 14


# ═══════════════════════════════════════════════════════════════
# Specific content checks
# ═══════════════════════════════════════════════════════════════

class TestSpecificContent:
    """Critical taboo entries must be present for key locales."""

    def test_zh_CN_has_taiwan_sensitivity(self):
        zh_words = get_taboo_words("zh-CN")
        # 台独 should be present
        assert any("台独" in w["word"] or "独" in w["contexts"] for w in zh_words), (
            "zh-CN must cover Taiwan-related political sensitivity"
        )

    def test_ar_SA_has_islamic_taboos(self):
        ar_words = get_taboo_words("ar-SA")
        assert len(ar_words) >= 3, "ar-SA must have Islamic taboo words"

    def test_ja_JP_has_burakumin(self):
        ja_words = get_taboo_words("ja-JP")
        assert any("部落" in w["word"] for w in ja_words), "ja-JP must cover burakumin"

    def test_en_US_has_racial_slurs(self):
        en_words = get_taboo_words("en-US")
        assert len(en_words) >= 4, "en-US must cover racial slur taboos"

    def test_number_4_is_taboo_east_asia(self):
        for locale in ["zh-CN", "ja-JP", "ko-KR"]:
            nums = get_taboo_numbers(locale)
            assert any(n["number"] == 4 for n in nums), f"{locale} must have 4 as taboo"

    def test_number_13_is_taboo_western(self):
        for locale in ["en-US", "en-GB"]:
            nums = get_taboo_numbers(locale)
            assert any(n["number"] == 13 for n in nums), f"{locale} must have 13 as taboo"

    def test_holocaust_taboo_words(self):
        he_words = get_taboo_words("he-IL")
        de_words = get_taboo_words("de-DE")
        assert any("שואה" in w["word"] for w in he_words), "he-IL must cover Holocaust"
        assert any("Hitler" in w["word"] for w in de_words), "de-DE must cover Nazi references"

    def test_ramadan_coverage(self):
        ar_holidays = get_taboo_holidays("ar-SA")
        assert any("Ramadan" in h["period"] or "斋月" in h["period"] for h in ar_holidays), (
            "ar-SA must cover Ramadan"
        )
