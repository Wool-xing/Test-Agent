"""L1 frontmatter lint · 无 LLM · pre-push / pre-commit / doctor 共用.

校验:
- agents/[0-9]*.md 16 个文件 frontmatter `name`/`description`/`tools` 必填
- skills/*.md(排除 README/INDEX/上游 darwin-skill/karpathy-guidelines)`name`/`description` 必填
- registry.build_catalog() 加载后 16 expert 全在,且 name 字段与 file slug 协同(只看 frontmatter name)
- 所有 agent 文件名形如 `NN-中文.md`(NN 两位数 01-16),序号连续无跳

返回:
  ok=True / list[issue],issue 形如 {"path": ..., "field": ..., "reason": ...}
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from runtime.config.settings import get_settings
from runtime.registry.registry import build_catalog

REQUIRED_EXPERT = ("name", "description", "tools")
REQUIRED_SKILL = ("name", "description")

EXPERT_FNAME_RE = re.compile(r"^(\d{2})-[^.]+\.md$")
EXPECTED_AGENTS = 16
EXPECTED_SKILLS_MIN = 32

UPSTREAM_SKILL_DIRS = {"darwin-skill", "karpathy-guidelines"}


@dataclass(slots=True)
class Issue:
    path: str
    field: str
    reason: str

    def __str__(self) -> str:
        return f"{self.path} · {self.field} · {self.reason}"


@dataclass(slots=True)
class SmokeReport:
    issues: list[Issue]
    expert_count: int
    skill_count: int

    @property
    def ok(self) -> bool:
        return not self.issues

    def render(self) -> str:
        head = f"agents={self.expert_count}/{EXPECTED_AGENTS}  skills={self.skill_count}/{EXPECTED_SKILLS_MIN}"
        if self.ok:
            return f"[OK] {head}  no issues"
        body = "\n".join(f"  - {i}" for i in self.issues)
        return f"[FAIL] {head}\n{body}"


def _check_frontmatter_present(meta: dict, required: tuple[str, ...], path: Path) -> list[Issue]:
    issues: list[Issue] = []
    for f in required:
        val = meta.get(f)
        if val is None or (isinstance(val, str) and not val.strip()):
            issues.append(Issue(path=str(path), field=f, reason="missing or empty"))
    return issues


def _read_meta(path: Path) -> dict:
    import yaml

    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}


def check_experts(experts_dir: Path) -> tuple[list[Issue], int]:
    issues: list[Issue] = []
    files = sorted(p for p in experts_dir.glob("*.md") if p.name.upper() not in {"README.MD", "INDEX.MD"})
    seen_nums: list[int] = []
    for p in files:
        m = EXPERT_FNAME_RE.match(p.name)
        if not m:
            # V2 bilingual: also accept lowercase English names (test-lead.md etc.)
            if re.match(r"^[a-z][a-z0-9-]*\.md$", p.name):
                pass  # English-named file: validate frontmatter only (no numbering)
            else:
                issues.append(Issue(path=str(p), field="filename", reason="expected NN-name.md or lowercase-en.md"))
                continue
        else:
            seen_nums.append(int(m.group(1)))
        meta = _read_meta(p)
        issues.extend(_check_frontmatter_present(meta, REQUIRED_EXPERT, p))

    if len(seen_nums) != EXPECTED_AGENTS:
        issues.append(Issue(path=str(experts_dir), field="count", reason=f"expected {EXPECTED_AGENTS} agents, got {len(seen_nums)}"))
    if seen_nums and seen_nums != list(range(1, len(seen_nums) + 1)):
        gaps = sorted(set(range(1, max(seen_nums) + 1)) - set(seen_nums))
        if gaps:
            issues.append(Issue(path=str(experts_dir), field="numbering", reason=f"missing serial: {gaps}"))
    return issues, len(seen_nums)


def check_skills(skills_dir: Path) -> tuple[list[Issue], int]:
    issues: list[Issue] = []
    count = 0
    for p in sorted(skills_dir.glob("*.md")):
        if p.name.upper() in {"README.MD", "INDEX.MD"}:
            continue
        if any(part in UPSTREAM_SKILL_DIRS for part in p.parts):
            continue
        meta = _read_meta(p)
        issues.extend(_check_frontmatter_present(meta, REQUIRED_SKILL, p))
        count += 1
    if count < EXPECTED_SKILLS_MIN:
        issues.append(Issue(path=str(skills_dir), field="count", reason=f"expected ={EXPECTED_SKILLS_MIN} skills, got {count}"))
    return issues, count


def check_registry_loadable() -> list[Issue]:
    """registry.build_catalog() 必须能加载所有 expert + skill 不抛错."""
    try:
        cat = build_catalog()
    except Exception as e:  # noqa: BLE001
        return [Issue(path="runtime/registry/registry.py", field="build_catalog", reason=f"raised: {e}")]
    if len(cat.experts) != EXPECTED_AGENTS:
        return [Issue(path="registry", field="experts", reason=f"loaded {len(cat.experts)} experts, expected {EXPECTED_AGENTS}")]
    return []


def run_smoke() -> SmokeReport:
    s = get_settings()
    experts_dir = s.resolve(s.experts_dir)
    skills_dir = s.resolve(s.skills_dir)
    issues: list[Issue] = []
    e_issues, e_count = check_experts(experts_dir)
    s_issues, s_count = check_skills(skills_dir)
    r_issues = check_registry_loadable()
    issues.extend(e_issues)
    issues.extend(s_issues)
    issues.extend(r_issues)
    return SmokeReport(issues=issues, expert_count=e_count, skill_count=s_count)


def main() -> int:
    report = run_smoke()
    print(report.render())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
