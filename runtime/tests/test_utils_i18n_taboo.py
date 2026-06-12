# SPDX-License-Identifier: MIT
"""Unit tests for i18n_checker.py Phase 5 — 神圣性与跨文化禁忌审计."""

from __future__ import annotations

import sys
from pathlib import Path

# utils package installed via pip install -e runtime/

from utils.a11y_i18n.i18n_checker import (  # noqa: E402
    audit_sacred_contexts,
    audit_taboo_colors,
    audit_taboo_holidays,
    audit_taboo_numbers,
    audit_taboo_words,
    run_taboo_audit,
)

# ═══════════════════════════════════════════════════════════════
# audit_taboo_words
# ═══════════════════════════════════════════════════════════════

class TestAuditTabooWords:
    """Scan text for taboo words per locale."""

    def test_detects_chinese_political_taboo(self):
        result = audit_taboo_words("台独主张", ["zh-CN"])
        assert result["hits"] >= 1
        finding = result["findings"][0]
        assert finding["locale"] == "zh-CN"
        assert finding["severity"] == "critical"

    def test_detects_japanese_discrimination_term(self):
        result = audit_taboo_words("気違いな行動", ["ja-JP"])
        assert result["hits"] >= 1
        assert any("気違い" in f["matched_word"] for f in result["findings"])

    def test_detects_english_racial_slur(self):
        result = audit_taboo_words("the nigger word", ["en-US"])
        assert result["hits"] >= 1
        assert any(f["severity"] == "critical" for f in result["findings"])

    def test_detects_german_nazi_taboo(self):
        result = audit_taboo_words("Heil Hitler", ["de-DE"])
        assert result["hits"] >= 1
        assert result["findings"][0]["locale"] == "de-DE"

    def test_detects_hindi_beef_taboo(self):
        result = audit_taboo_words("beef meat", ["hi-IN"])
        assert result["hits"] >= 1

    def test_detects_thai_lese_majeste(self):
        result = audit_taboo_words("หมิ่นพระบรมเดชานุภาพ", ["th-TH"])
        assert result["hits"] >= 1
        assert result["findings"][0]["severity"] == "critical"

    def test_clean_text_returns_no_hits(self):
        result = audit_taboo_words("hello world 你好", ["en-US", "zh-CN"])
        assert result["hits"] == 0

    def test_scan_all_locales_when_none_specified(self):
        result = audit_taboo_words("beef sandwich")
        assert result["hits"] >= 1  # hi-IN: beef

    def test_empty_text_returns_zero_hits(self):
        result = audit_taboo_words("", ["zh-CN"])
        assert result["hits"] == 0

    def test_case_insensitive_matching(self):
        result = audit_taboo_words("HEIL HITLER", ["de-DE"])
        assert result["hits"] >= 1

    def test_multiple_locales_scan(self):
        result = audit_taboo_words("台独 beef", ["zh-CN", "hi-IN"])
        assert result["hits"] >= 2


# ═══════════════════════════════════════════════════════════════
# audit_taboo_colors
# ═══════════════════════════════════════════════════════════════

class TestAuditTabooColors:
    """Check color usage against cultural taboo matrix."""

    def test_white_is_taboo_in_east_asia(self):
        result = audit_taboo_colors(["white"], ["zh-CN"])
        assert result["hits"] >= 1
        assert any(f["color"] == "white" for f in result["findings"])

    def test_white_is_taboo_in_japan(self):
        result = audit_taboo_colors(["white"], ["ja-JP"])
        assert result["hits"] >= 1

    def test_white_is_taboo_in_india(self):
        result = audit_taboo_colors(["white"], ["hi-IN"])
        assert result["hits"] >= 1
        assert any(f["severity"] == "critical" for f in result["findings"])

    def test_red_name_writing_taboo_in_korea(self):
        result = audit_taboo_colors(["red"], ["ko-KR"])
        assert result["hits"] >= 1
        assert any("名字" in f["context"] or "name" in f["reason"].lower() for f in result["findings"])

    def test_green_is_sacred_in_arabic(self):
        result = audit_taboo_colors(["green"], ["ar-SA"])
        assert result["hits"] >= 1
        assert any(f["severity"] == "critical" for f in result["findings"])

    def test_safe_colors_return_no_hits(self):
        result = audit_taboo_colors(["blue", "teal", "orange"], ["en-US"])
        assert result["hits"] == 0

    def test_mixed_locales_multiple_hits(self):
        result = audit_taboo_colors(["white"], ["zh-CN", "hi-IN"])
        assert result["hits"] >= 2

    def test_case_insensitive_color_matching(self):
        result = audit_taboo_colors(["WHITE", "Red"], ["zh-CN"])
        assert result["hits"] >= 2  # white + red both taboo in zh-CN

    def test_all_locales_scan(self):
        result = audit_taboo_colors(["purple"])
        assert result["hits"] >= 2  # th-TH + pt-BR + it-IT


# ═══════════════════════════════════════════════════════════════
# audit_taboo_numbers
# ═══════════════════════════════════════════════════════════════

class TestAuditTabooNumbers:
    """Check numbers against cultural taboo matrix."""

    def test_4_is_taboo_in_chinese(self):
        result = audit_taboo_numbers([4], ["zh-CN"])
        assert result["hits"] >= 1
        assert result["findings"][0]["matched_taboo"] == 4

    def test_4_is_taboo_in_japanese(self):
        result = audit_taboo_numbers([4], ["ja-JP"])
        assert result["hits"] >= 1

    def test_4_is_taboo_in_korean(self):
        result = audit_taboo_numbers([4], ["ko-KR"])
        assert result["hits"] >= 1

    def test_13_is_taboo_western(self):
        result = audit_taboo_numbers([13], ["en-US"])
        assert result["hits"] >= 1
        assert result["findings"][0]["matched_taboo"] == 13

    def test_666_is_taboo_christian(self):
        result = audit_taboo_numbers([666], ["en-US"])
        assert result["hits"] >= 1
        assert result["findings"][0]["severity"] == "high"

    def test_8_in_funeral_context_is_taboo(self):
        result = audit_taboo_numbers([8], ["zh-CN"])
        assert result["hits"] >= 1

    def test_safe_numbers_return_no_hits(self):
        result = audit_taboo_numbers([1, 2, 3, 5], ["en-US"])
        assert result["hits"] == 0

    def test_containment_matching_14_contains_4(self):
        result = audit_taboo_numbers([14], ["zh-CN"])
        # 14 contains 4 and also 14 is a separate taboo in zh-CN
        assert result["hits"] >= 1

    def test_containment_matching_1401_contains_4_and_14(self):
        result = audit_taboo_numbers([1401], ["zh-CN"])
        assert result["hits"] >= 1  # 4 is in 1401, 14 is also

    def test_multiple_numbers_multiple_locales(self):
        result = audit_taboo_numbers([4, 13, 17], ["zh-CN", "en-US", "it-IT"])
        assert result["hits"] >= 3

    def test_zero_is_taboo_in_red_envelope(self):
        result = audit_taboo_numbers([0], ["zh-CN"])
        assert result["hits"] >= 1


# ═══════════════════════════════════════════════════════════════
# audit_taboo_holidays
# ═══════════════════════════════════════════════════════════════

class TestAuditTabooHolidays:
    """Check date against taboo holiday periods."""

    def test_qingming_date(self):
        """清明节 4月4-5日 should match."""
        result = audit_taboo_holidays("04-05", ["zh-CN"])
        assert result["hits"] >= 1
        assert any("清明" in f["matched_period"] for f in result["findings"])

    def test_september_18_china(self):
        """九一八 9月18日 should match."""
        result = audit_taboo_holidays("09-18", ["zh-CN"])
        assert result["hits"] >= 1
        assert any(f["severity"] == "critical" for f in result["findings"])

    def test_nanjing_massacre_day(self):
        """南京公祭日 12月13日 should match."""
        result = audit_taboo_holidays("12-13", ["zh-CN"])
        assert result["hits"] >= 1
        assert any(f["severity"] == "critical" for f in result["findings"])

    def test_hiroshima_day(self):
        """广岛原爆 8月6日 should match."""
        result = audit_taboo_holidays("08-06", ["ja-JP"])
        assert result["hits"] >= 1
        assert any(f["severity"] == "critical" for f in result["findings"])

    def test_nagasaki_day(self):
        """长崎原爆 8月9日 should match."""
        result = audit_taboo_holidays("08-09", ["ja-JP"])
        assert result["hits"] >= 1

    def test_sept_11_us(self):
        """9/11 should match."""
        result = audit_taboo_holidays("09-11", ["en-US"])
        assert result["hits"] >= 1
        assert any(f["severity"] == "critical" for f in result["findings"])

    def test_victory_day_russia(self):
        """5月9日 胜利日 should match."""
        result = audit_taboo_holidays("05-09", ["ru-RU"])
        assert result["hits"] >= 1

    def test_ordinary_day_returns_no_hits(self):
        result = audit_taboo_holidays("03-15", ["zh-CN", "en-US"])
        assert result["hits"] == 0

    def test_given_date_range_qingming(self):
        """清明节 range 4月4-5日 — 4月4日 should also match."""
        result = audit_taboo_holidays("04-04", ["zh-CN"])
        assert result["hits"] >= 1


# ═══════════════════════════════════════════════════════════════
# audit_sacred_contexts
# ═══════════════════════════════════════════════════════════════

class TestAuditSacredContexts:
    """Check context descriptions against sacredness rules."""

    def test_funeral_context_matches_global_rule(self):
        result = audit_sacred_contexts("葬礼", "zh-CN")
        assert result["hits"] >= 1

    def test_children_context_matches_global_rule(self):
        result = audit_sacred_contexts("儿童用户", "*")
        assert result["hits"] >= 1
        assert any(f["severity"] == "critical" for f in result["findings"])

    def test_tiananmen_context(self):
        result = audit_sacred_contexts("天安门广场", "zh-CN")
        assert result["hits"] >= 1

    def test_mecca_context(self):
        result = audit_sacred_contexts("麦加", "ar-SA")
        assert result["hits"] >= 1
        assert any(f["severity"] == "critical" for f in result["findings"])

    def test_western_wall_context(self):
        result = audit_sacred_contexts("哭墙", "he-IL")
        assert result["hits"] >= 1

    def test_irrelevant_context_returns_no_hits(self):
        result = audit_sacred_contexts("咖啡店", "zh-CN")
        assert result["hits"] == 0

    def test_global_wildcard_locale_includes_global_rules(self):
        result = audit_sacred_contexts("宗教场所", "*")
        assert result["hits"] >= 1

    def test_bidirectional_matching(self):
        result = audit_sacred_contexts("殡仪馆", "zh-CN")
        assert result["hits"] >= 1


# ═══════════════════════════════════════════════════════════════
# run_taboo_audit (combined entry point)
# ═══════════════════════════════════════════════════════════════

class TestRunTabooAudit:
    """Combined taboo audit with full payload."""

    def test_full_payload_returns_all_dimensions(self):
        payload = {
            "text": "Hello world test",
            "colors": ["white"],
            "numbers": [4, 13],
            "context": "宗教场所",
            "locales": ["zh-CN", "en-US", "ar-SA"],
        }
        result = run_taboo_audit(payload)
        assert "taboo_words" in result
        assert "taboo_colors" in result
        assert "taboo_numbers" in result
        assert "taboo_holidays" in result
        assert "sacred_contexts" in result
        assert "matrix_summary" in result
        assert "supported_locales" in result
        assert result["phase"] == 5
        assert result["audit_name"] == "sacredness_cross_cultural_taboo"
        assert result["total_hits"] > 0

    def test_minimal_payload(self):
        result = run_taboo_audit({})
        assert result["total_hits"] == 0  # no data to scan
        assert "taboo_holidays" in result  # still runs with today's date

    def test_text_only_payload(self):
        result = run_taboo_audit({"text": "台独 nigger"})
        assert result["taboo_words"]["hits"] >= 2

    def test_total_hits_aggregates_correctly(self):
        payload = {
            "text": "beef台独",
            "colors": ["white"],
            "numbers": [4],
            "locales": ["zh-CN", "hi-IN"],
        }
        result = run_taboo_audit(payload)
        expected = (
            result["taboo_words"]["hits"]
            + result["taboo_colors"]["hits"]
            + result["taboo_numbers"]["hits"]
            + result["taboo_holidays"]["hits"]
        )
        assert result["total_hits"] == expected

    def test_locale_filter_applied_to_all_dimensions(self):
        payload = {
            "text": "台独 beef nigger",
            "colors": ["white", "green"],
            "numbers": [4, 13],
            "locales": ["zh-CN"],
        }
        result = run_taboo_audit(payload)
        # Only zh-CN violations should register
        for finding in result["taboo_words"]["findings"]:
            assert finding["locale"] == "zh-CN"
        for finding in result["taboo_colors"]["findings"]:
            assert finding["locale"] == "zh-CN"
        for finding in result["taboo_numbers"]["findings"]:
            assert finding["locale"] == "zh-CN"

    def test_sacred_context_uses_first_locale(self):
        payload = {
            "context": "殡仪馆",
            "locales": ["zh-CN", "en-US"],
        }
        result = run_taboo_audit(payload)
        assert result["sacred_contexts"]["hits"] >= 1
        assert result["sacred_contexts"]["locale_filter"] == "zh-CN"
