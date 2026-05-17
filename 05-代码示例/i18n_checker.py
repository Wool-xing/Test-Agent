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


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="i18n / l10n 检查")
    sub = parser.add_subparsers(dest="cmd")
    k = sub.add_parser("keys"); k.add_argument("--ref", default="en-US"); k.add_argument("--dir", default="workspace/自动化脚本/python/i18n")
    h = sub.add_parser("hardcoded"); h.add_argument("--dir", default="./src")
    args = parser.parse_args()
    if args.cmd == "keys":
        print(json.dumps(check_translation_keys(args.ref, args.dir), indent=2, ensure_ascii=False))
    elif args.cmd == "hardcoded":
        print(json.dumps(detect_hardcoded_strings(args.dir), indent=2, ensure_ascii=False))
