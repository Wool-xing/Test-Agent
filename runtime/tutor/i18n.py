"""Language switching · 主宪章 §23.

zh / en / zh-en(double-column comparison)
"""

from __future__ import annotations

import os
from typing import Literal

Lang = Literal["zh", "en", "zh-en"]

UI_STRINGS = {
    "zh": {
        "step": "步骤",
        "why": "原因",
        "theory": "理论",
        "alternatives": "替代",
        "reading": "深度阅读",
        "feedback_button": "👎 标记错误",
        "not_in_kb": "该领域未收录 KB,慎用",
        "decision_replay": "决策回放",
        "exec_one_liner": "一句话",
    },
    "en": {
        "step": "Step",
        "why": "Why",
        "theory": "Theory",
        "alternatives": "Alternatives",
        "reading": "Further reading",
        "feedback_button": "👎 Flag as wrong",
        "not_in_kb": "Not in KB — use with caution",
        "decision_replay": "Decision replay",
        "exec_one_liner": "One-liner",
    },
}


def get_lang() -> Lang:
    raw = os.getenv("TAGENT_LANG", "zh").lower()
    if raw in ("zh", "zh-cn", "chinese", "中文"):
        return "zh"
    if raw in ("en", "english", "英文"):
        return "en"
    if raw in ("zh-en", "bilingual", "双语"):
        return "zh-en"
    return "zh"


def set_lang(lang: Lang | str) -> None:
    os.environ["TAGENT_LANG"] = str(lang).lower()


def t(key: str, lang: Lang | None = None) -> str:
    lang = lang or get_lang()
    if lang == "zh-en":
        zh = UI_STRINGS["zh"].get(key, key)
        en = UI_STRINGS["en"].get(key, key)
        return f"{zh} / {en}"
    return UI_STRINGS.get(lang, UI_STRINGS["zh"]).get(key, key)


def card_text(card, field_zh: str, field_en: str, lang: Lang | None = None) -> str:
    """Pick zh/en/both from a Card."""
    lang = lang or get_lang()
    zh = getattr(card, field_zh, "") or ""
    en = getattr(card, field_en, "") or ""
    if lang == "zh-en":
        return f"{zh}\n{en}".strip()
    if lang == "en":
        return en or zh
    return zh or en
