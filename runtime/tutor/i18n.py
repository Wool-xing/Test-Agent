"""Language switching.

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
        "lang_switched": "语言已切换为",
        "lang_available": "可用语言: zh(中文) / en(English) / zh-en(双语)",
        "undo_help": "移除最后一轮对话, 可多次回退",
        "retry_help": "撤回助手回复并用相同提示词重试",
        "gateway_help": "显示9平台IM网关连接状态",
        "resume_help": "加载已保存会话继续对话",
        "distill_help": "将上次执行提炼为可复用Skill",
        "nudge_help": "扫描对话, 建议保存重要事实到MEMORY.md",
        "personality_help": "切换Agent专家人格",
        "doctor_help": "7维度环境健康诊断",
        "insights_help": "跨会话使用数据分析",
        "search_help": "全文检索历史对话",
        "sessions_help": "列出已保存会话",
        "remember_help": "保存事实到MEMORY.md",
        "forget_help": "按关键词删除记忆",
        "memory_help": "查看MEMORY.md内容",
        "clear_help": "重置会话记忆",
        "model_help": "切换LLM提供商/模型",
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
        "lang_switched": "Language switched to",
        "lang_available": "Available: zh(中文) / en(English) / zh-en(Bilingual)",
        "undo_help": "Remove last exchange, can unwind multiple turns",
        "retry_help": "Undo assistant response and retry with same prompt",
        "gateway_help": "Show 9-platform IM gateway connection status",
        "resume_help": "Load a saved session to continue",
        "distill_help": "Distill last execution into a reusable skill",
        "nudge_help": "Scan conversation for facts worth remembering",
        "personality_help": "Switch agent expert persona",
        "doctor_help": "7-category environment health check",
        "insights_help": "Cross-session usage analytics",
        "search_help": "Full-text search across conversation history",
        "sessions_help": "List saved sessions",
        "remember_help": "Save fact to MEMORY.md",
        "forget_help": "Remove facts by keyword",
        "memory_help": "Show MEMORY.md contents",
        "clear_help": "Reset conversation memory",
        "model_help": "Switch LLM provider/model",
    },
}


def get_lang() -> Lang:
    raw = os.getenv("TAGENT_LANG", "").lower()
    if raw in ("zh", "zh-cn", "chinese", "中文"):
        return "zh"
    if raw in ("en", "english", "英文"):
        return "en"
    if raw in ("zh-en", "bilingual", "双语"):
        return "zh-en"
    if raw:
        return "zh"  # unknown value → default zh
    # Auto-detect from system locale
    try:
        import locale
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            loc = locale.getdefaultlocale()[0] or ""
        if loc.lower().startswith("zh"):
            return "zh"
    except Exception:
        pass
    return "en"  # global non-Chinese default


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
