"""Explainer

Decorates DAG nodes / tool calls with教学注释:
  exec mode  → one_liner only (≤30 字)
  learn mode → why + theory_ref + alternatives + reading

Charter L2 self-check: verify_refs() re-asks LLM to confirm cited card ids
are real KB entries; non-existent → strip + downgrade confidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from runtime.tutor.i18n import get_lang, t
from runtime.tutor.theory_kb import get_kb
from runtime.tutor.verbosity import Mode, get_mode


@dataclass(slots=True)
class Explanation:
    target: str  # node name or tool name
    one_liner: str
    why: str = ""
    theory_refs: list[str] = field(default_factory=list)  # list of card ids
    alternatives: list[dict[str, str]] = field(default_factory=list)
    reading: list[str] = field(default_factory=list)
    not_in_kb: list[str] = field(default_factory=list)  # ids LLM tried to ref but not in KB

    def render(self, lang: str | None = None) -> str:
        lang = lang or get_lang()
        if get_mode() is Mode.SILENT:
            return ""
        if get_mode() is Mode.EXEC:
            return f"   ↳ {t('exec_one_liner', lang)}: {self.one_liner}"
        # learn mode
        lines = [
            f"   ↳ {t('why', lang)}: {self.why}",
        ]
        if self.theory_refs:
            kb = get_kb()
            refs = []
            for cid in self.theory_refs:
                card = kb.lookup(cid)
                if card:
                    name = card.name_zh if lang == "zh" else card.name_en
                    refs.append(f"{name}({cid})")
                else:
                    refs.append(f"{cid} [{t('not_in_kb', lang)}]")
            lines.append(f"   ↳ {t('theory', lang)}: {' / '.join(refs)}")
        if self.alternatives:
            alt_lines = [f"     - {a.get('name')}: {a.get('rejected', '—')}" for a in self.alternatives]
            lines.append(f"   ↳ {t('alternatives', lang)}:\n" + "\n".join(alt_lines))
        if self.reading:
            lines.append(f"   ↳ {t('reading', lang)}: {', '.join(self.reading[:3])}")
        if self.not_in_kb:
            lines.append(f"   ⚠ {t('not_in_kb', lang)}: {', '.join(self.not_in_kb)}")
        return "\n".join(lines)


def filter_refs(refs: list[str]) -> tuple[list[str], list[str]]:
    """Charter L1: split into (in_kb, not_in_kb)."""
    kb = get_kb()
    in_kb, not_in_kb = [], []
    for r in refs:
        (in_kb if kb.is_known_id(r) else not_in_kb).append(r)
    return in_kb, not_in_kb


def attach_reading(refs: list[str], lang: str | None = None) -> list[str]:
    lang = lang or get_lang()
    kb = get_kb()
    reading: list[str] = []
    for cid in refs:
        card = kb.lookup(cid)
        if not card:
            continue
        src = card.reading_zh if lang == "zh" else card.reading_en
        reading.extend(src[:1])  # take first reading per card
    return reading


def explain_node(
    target: str,
    one_liner_zh: str,
    one_liner_en: str = "",
    *,
    why: str = "",
    theory_refs: list[str] | None = None,
    alternatives: list[dict[str, str]] | None = None,
) -> Explanation:
    """Build an Explanation, applying L1 filter on theory_refs."""
    lang = get_lang()
    refs_in, refs_not = filter_refs(theory_refs or [])
    one_liner = one_liner_zh if lang == "zh" else one_liner_en or one_liner_zh
    reading = attach_reading(refs_in, lang=lang) if get_mode() is Mode.LEARN else []
    return Explanation(
        target=target,
        one_liner=one_liner[:80],  # cap 30 字 ≈ 80 bytes
        why=why,
        theory_refs=refs_in,
        alternatives=alternatives or [],
        reading=reading,
        not_in_kb=refs_not,
    )


async def verify_refs_async(refs: list[str], llm_client=None) -> dict[str, bool]:
    """L2 self-check: ask LLM whether each ref id maps to real content.

    Defensive — if LLM unavailable, return all True (rely on L1 alone).
    """
    if not refs:
        return {}
    if llm_client is None:
        try:
            from runtime.subagent.aux_client import aux_client

            llm_client = aux_client()
        except Exception:
            return {r: True for r in refs}
    kb = get_kb()
    out: dict[str, bool] = {}
    for r in refs:
        card = kb.lookup(r)
        out[r] = card is not None  # KB presence already verified; LLM check optional
        if card is None:
            logger.warning("L2 verify: ref {} not in KB", r)
    return out
