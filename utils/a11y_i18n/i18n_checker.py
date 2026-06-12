# SPDX-License-Identifier: MIT
"""
国际化（i18n）/ 本地化（l10n）测试
被引用方：UX / 兼容 / 全球化产品

检查：
- 多语言资源文件完整性（key 一致）
- 字符串硬编码检测
- 字符串截断 / 文本溢出（动态长度）
- 日期 / 货币 / 数字格式
- RTL（阿拉伯语 / 希伯来语）
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


# ===== 多语言资源完整性 =====

def check_translation_keys(reference_lang: str = "en-US",
                            locales_dir: str = "workspace/自动化脚本/python/i18n") -> Dict:
    """
    检查所有语言文件的 key 是否与 reference 一致（缺失 / 多余）。
    locales_dir 下：en-US.json / zh-CN.json / ja-JP.json ...
    """
    base_path = Path(locales_dir)
    if not base_path.exists():
        return {"error": f"{locales_dir} 不存在"}

    ref_file = base_path / f"{reference_lang}.json"
    if not ref_file.exists():
        return {"error": f"参考语言 {reference_lang} 文件不存在"}

    ref_keys = _flatten_keys(json.loads(ref_file.read_text(encoding="utf-8")))
    issues = {}

    for f in base_path.glob("*.json"):
        lang = f.stem
        if lang == reference_lang:
            continue
        keys = _flatten_keys(json.loads(f.read_text(encoding="utf-8")))
        missing = ref_keys - keys
        extra = keys - ref_keys
        if missing or extra:
            issues[lang] = {
                "missing_keys": sorted(missing)[:20],
                "extra_keys": sorted(extra)[:20],
                "missing_count": len(missing),
                "extra_count": len(extra),
            }
    return {"reference": reference_lang, "issues": issues, "languages_checked": len(issues)}


def _flatten_keys(d: Dict, prefix: str = "") -> Set[str]:
    keys = set()
    for k, v in d.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys |= _flatten_keys(v, full)
        else:
            keys.add(full)
    return keys


# ===== 硬编码字符串检测 =====

def detect_hardcoded_strings(src_dir: str = "./src",
                              extensions: List[str] = None) -> Dict:
    """
    扫源码，检测可能未走 i18n 的硬编码中文字符串。
    """
    extensions = extensions or [".py", ".js", ".ts", ".jsx", ".tsx", ".vue"]
    chinese_pattern = re.compile(r'["\']([^"\']*[一-鿿]+[^"\']*)["\']')

    findings = []
    for ext in extensions:
        for f in Path(src_dir).rglob(f"*{ext}"):
            try:
                text = f.read_text(encoding="utf-8")
                for m in chinese_pattern.finditer(text):
                    findings.append({
                        "file": str(f.relative_to(src_dir)),
                        "string": m.group(1)[:80],
                    })
            except (UnicodeDecodeError, PermissionError, OSError) as e:
                logger.warning("i18n scan skipped %s: %s", f.relative_to(src_dir), e)
    return {
        "src_dir": src_dir,
        "hardcoded_count": len(findings),
        "samples": findings[:30],
    }


# ===== 字符串膨胀检测（动态长度 → 文本溢出 / 截断）=====

# 经验：英 → 德 +35%、英 → 法 +25%、英 → 中 -20%
EXPANSION_RATIO = {
    "de-DE": 1.35, "fr-FR": 1.25, "es-ES": 1.30,
    "ru-RU": 1.40, "zh-CN": 0.7, "ja-JP": 0.6, "ar-SA": 1.20,
}


def predict_text_overflow(reference_text: str, target_lang: str,
                           ui_max_width_chars: int) -> Dict:
    """根据膨胀率预测目标语言下是否文本溢出"""
    ratio = EXPANSION_RATIO.get(target_lang, 1.0)
    estimated = int(len(reference_text) * ratio)
    return {
        "reference_length": len(reference_text),
        "target_lang": target_lang,
        "estimated_length": estimated,
        "ui_max": ui_max_width_chars,
        "may_overflow": estimated > ui_max_width_chars,
    }


# ===== RTL 检查 =====

RTL_LANGUAGES = {"ar-SA", "he-IL", "fa-IR", "ur-PK"}


def is_rtl(lang_code: str) -> bool:
    return lang_code in RTL_LANGUAGES


# ===== 日期 / 货币 / 数字格式 =====

def format_check_examples(lang: str) -> Dict:
    """各语言下的日期 / 货币 / 数字预期格式（参考）"""
    formats = {
        "en-US": {"date": "MM/DD/YYYY", "currency": "$1,234.56", "decimal": "1,234.56"},
        "zh-CN": {"date": "YYYY-MM-DD", "currency": "¥1,234.56", "decimal": "1,234.56"},
        "de-DE": {"date": "DD.MM.YYYY", "currency": "1.234,56 €", "decimal": "1.234,56"},
        "ja-JP": {"date": "YYYY/MM/DD", "currency": "¥1,234", "decimal": "1,234"},
        "ar-SA": {"date": "DD/MM/YYYY", "currency": "ر.س 1,234.56", "decimal": "1,234.56"},
    }
    return formats.get(lang, formats["en-US"])


# ═══════════════════════════════════════════════════════════════
# Phase 5: 神圣性与跨文化禁忌审计 (taboo audit)
# ═══════════════════════════════════════════════════════════════

def _load_taboo_matrix():
    """Lazy-load taboo_matrix to avoid circular import at module level."""
    from utils.design.taboo_matrix import (
        TABOO_WORDS, TABOO_COLORS, TABOO_NUMBERS,
        TABOO_HOLIDAYS, SACRED_CONTEXTS,
        get_matrix_summary, get_supported_locales,
    )
    return TABOO_WORDS, TABOO_COLORS, TABOO_NUMBERS, TABOO_HOLIDAYS, SACRED_CONTEXTS, get_matrix_summary, get_supported_locales


def audit_taboo_words(text: str, locales: List[str] | None = None) -> Dict:
    """
    扫描文本中的禁忌词，返回命中列表。
    locales=None 即查全部 locale。
    """
    TABOO_WORDS, _, _, _, _, _, _ = _load_taboo_matrix()
    findings = []
    for entry in TABOO_WORDS:
        if locales and entry["locale"] not in locales:
            continue
        word = entry["word"]
        if isinstance(word, str) and word.lower() in text.lower():
            findings.append({
                "locale": entry["locale"],
                "matched_word": word,
                "severity": entry["severity"],
                "reason": entry["reason"],
                "contexts": entry.get("contexts", []),
            })
    return {
        "text_length": len(text),
        "locales_scanned": locales or "all",
        "hits": len(findings),
        "findings": findings,
    }


def audit_taboo_colors(colors_used: list[str], locales: List[str] | None = None) -> Dict:
    """
    检查所用颜色是否触及各 locale 禁忌。
    colors_used: ['white', 'red', '#FF0000', ...]
    """
    _, TABOO_COLORS, _, _, _, _, _ = _load_taboo_matrix()
    findings = []
    for entry in TABOO_COLORS:
        if locales and entry["locale"] not in locales:
            continue
        color = entry["color"]
        if isinstance(color, str) and color.lower() in [c.lower() for c in colors_used]:
            findings.append({
                "locale": entry["locale"],
                "color": color,
                "context": entry.get("context", ""),
                "severity": entry["severity"],
                "reason": entry["reason"],
            })
    return {
        "colors_checked": colors_used,
        "locales_scanned": locales or "all",
        "hits": len(findings),
        "findings": findings,
    }


def audit_taboo_numbers(numbers: list[int], locales: List[str] | None = None) -> Dict:
    """
    检查数字（定价/楼层/编号）是否触及禁忌。
    自动检测包含关系 (如 1401→14, 413→4&13)。
    """
    _, _, TABOO_NUMBERS, _, _, _, _ = _load_taboo_matrix()
    findings = []
    for entry in TABOO_NUMBERS:
        if locales and entry["locale"] not in locales:
            continue
        tn = entry["number"]
        for n in numbers:
            if n == tn or (tn != 0 and str(tn) in str(n)):
                findings.append({
                    "locale": entry["locale"],
                    "number_used": n,
                    "matched_taboo": tn,
                    "context": entry.get("context", ""),
                    "severity": entry["severity"],
                    "reason": entry["reason"],
                })
                break
    return {
        "numbers_checked": numbers,
        "locales_scanned": locales or "all",
        "hits": len(findings),
        "findings": findings,
    }


def audit_taboo_holidays(date_str: str | None = None, locales: List[str] | None = None) -> Dict:
    """
    检查给定日期是否落入敏感时段。date_str='MM-DD' 或 ISO date。
    未传参则为今天。
    """
    from datetime import date as _date, datetime as _dt
    _, _, _, TABOO_HOLIDAYS, _, _, _ = _load_taboo_matrix()

    if date_str is None:
        today = _date.today()
    elif "-" in date_str and len(date_str) == 5:
        today = _dt.strptime(f"{_date.today().year}-{date_str}", "%Y-%m-%d").date()
    else:
        today = _dt.fromisoformat(date_str).date()

    findings = []
    month, day = today.month, today.day

    # Simple month-day matching for fixed-date taboo periods
    # Lunar calendar entries are approximate (lunar month ≈ solar month offset)
    for entry in TABOO_HOLIDAYS:
        if locales and entry["locale"] not in locales:
            continue
        period = entry["period"]
        # Extract month-day patterns from period string
        if _date_matches_period(month, day, period):
            findings.append({
                "locale": entry["locale"],
                "matched_period": period,
                "restriction": entry["restriction"],
                "severity": entry["severity"],
                "reason": entry["reason"],
            })
    return {
        "date": today.isoformat(),
        "locales_scanned": locales or "all",
        "hits": len(findings),
        "findings": findings,
    }


def _date_matches_period(month: int, day: int, period: str) -> bool:
    """Check if (month, day) matches a date pattern in period description."""
    import re as _re
    # Pattern: "8月6日/9日" — same month, multiple days separated by /
    m = _re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*/\s*(\d{1,2})\s*日", period)
    if m:
        mth, d1, d2 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return month == mth and (day == d1 or day == d2)
    # Match patterns like "4月4-5日" / "8月6日" / "12月13日" / "9月11日"
    m = _re.search(r"(\d{1,2})\s*月\s*(\d{1,2})[-−~]\s*(\d{1,2})\s*日", period)
    if m:
        mth, start_d, end_d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return month == mth and start_d <= day <= end_d
    m = _re.search(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日", period)
    if m:
        return month == int(m.group(1)) and day == int(m.group(2))
    # Western format: "11月11日" etc.
    return False


def audit_sacred_contexts(context_description: str, locale: str = "*") -> Dict:
    """
    检查场景描述是否触及神圣性规则。locale='*' 匹配全局规则。
    """
    _, _, _, _, SACRED_CONTEXTS, _, _ = _load_taboo_matrix()
    findings = []
    for entry in SACRED_CONTEXTS:
        if entry["locale"] != "*" and entry["locale"] != locale:
            continue
        ctx = entry["context"]
        # Check bidirectional: desc in ctx OR ctx in desc (e.g. "葬礼" matches "葬礼/追悼会")
        desc_lower = context_description.lower()
        ctx_lower = ctx.lower()
        if desc_lower in ctx_lower or ctx_lower in desc_lower:
            findings.append({
                "matched_context": ctx,
                "rule": entry["rule"],
                "severity": entry["severity"],
                "reason": entry["reason"],
            })
    return {
        "context": context_description,
        "locale_filter": locale,
        "hits": len(findings),
        "findings": findings,
    }


def run_taboo_audit(payload: Dict) -> Dict:
    """
    Phase 5 统一入口：执行全维度禁忌审计。

    payload 结构:
    {
        "text": "<待扫描文本>",
        "colors": ["white", "red"],
        "numbers": [4, 13, 666],
        "date": "04-05",       # 可选 MM-DD
        "context": "宗教场所",
        "locales": ["zh-CN", "ar-SA"]
    }
    """
    locales = payload.get("locales")
    results = {}

    text = payload.get("text", "")
    if text:
        results["taboo_words"] = audit_taboo_words(text, locales)

    colors = payload.get("colors", [])
    if colors:
        results["taboo_colors"] = audit_taboo_colors(colors, locales)

    numbers = payload.get("numbers", [])
    if numbers:
        results["taboo_numbers"] = audit_taboo_numbers(numbers, locales)

    date_str = payload.get("date")
    results["taboo_holidays"] = audit_taboo_holidays(date_str, locales)

    context = payload.get("context", "")
    if context:
        results["sacred_contexts"] = audit_sacred_contexts(context, locales[0] if locales else "*")

    _, _, _, _, _, get_matrix_summary, get_supported_locales = _load_taboo_matrix()
    results["matrix_summary"] = get_matrix_summary()
    results["supported_locales"] = get_supported_locales()

    total_hits = sum(r.get("hits", 0) for r in results.values() if isinstance(r, dict))
    results["total_hits"] = total_hits
    results["phase"] = 5
    results["audit_name"] = "sacredness_cross_cultural_taboo"

    return results


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="i18n / l10n 检查")
    sub = parser.add_subparsers(dest="cmd")
    k = sub.add_parser("keys"); k.add_argument("--ref", default="en-US"); k.add_argument("--dir", default="workspace/自动化脚本/python/i18n")
    h = sub.add_parser("hardcoded"); h.add_argument("--dir", default="./src")
    t = sub.add_parser("taboo"); t.add_argument("--text", default=""); t.add_argument("--colors", default=""); t.add_argument("--numbers", default=""); t.add_argument("--date", default=None); t.add_argument("--context", default=""); t.add_argument("--locales", default=None)
    args = parser.parse_args()
    if args.cmd == "keys":
        print(json.dumps(check_translation_keys(args.ref, args.dir), indent=2, ensure_ascii=False))
    elif args.cmd == "hardcoded":
        print(json.dumps(detect_hardcoded_strings(args.dir), indent=2, ensure_ascii=False))
    elif args.cmd == "taboo":
        payload = {"text": args.text}
        if args.colors:
            payload["colors"] = [c.strip() for c in args.colors.split(",")]
        if args.numbers:
            payload["numbers"] = [int(n.strip()) for n in args.numbers.split(",")]
        if args.date:
            payload["date"] = args.date
        if args.context:
            payload["context"] = args.context
        if args.locales:
            payload["locales"] = [l.strip() for l in args.locales.split(",")]
        print(json.dumps(run_taboo_audit(payload), indent=2, ensure_ascii=False))
