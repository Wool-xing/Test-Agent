"""analyze-usage.py · 输入 users-2026-05.csv → 出 W3 砍/留 决策矩阵.

依赖:pandas / matplotlib(可选)

输入(脱敏):
  users-2026-05.csv:user_hash, industry, team_size_bucket, registered_month, channel
  skill-usage-2026-05.csv:skill_name, unique_users, total_invocations, user_pct

输出:
  W3-cut-list.md:必砍 / 标 deprecated / 保留 三档
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path


def load_csv(path: Path) -> list[dict]:
    if not path.is_file():
        print(f"missing: {path}", file=sys.stderr)
        return []
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def analyze_users(users: list[dict]) -> dict:
    n = len(users)
    industries = Counter(u.get("industry", "unknown") for u in users)
    team_sizes = Counter(u.get("team_size_bucket", "unknown") for u in users)
    channels = Counter(u.get("acquisition_channel", "unknown") for u in users)
    return {
        "total": n,
        "industries": dict(industries.most_common(10)),
        "team_sizes": dict(team_sizes),
        "channels": dict(channels.most_common(10)),
    }


def cut_decision(skill_usage: list[dict]) -> dict:
    """W3 砍/留 决策.

    重度(≥10% 用户): keep + 文档加强
    中度(3-10%):     keep + 不主推
    长尾(<3%):       deprecated 月观察
    0%: archive
    """
    keep_core: list[str] = []
    keep_mid: list[str] = []
    deprecate: list[str] = []
    archive: list[str] = []
    for row in skill_usage:
        name = row["skill_name"]
        pct = float(row.get("user_pct", 0))
        if pct >= 10:
            keep_core.append(name)
        elif pct >= 3:
            keep_mid.append(name)
        elif pct > 0:
            deprecate.append(name)
        else:
            archive.append(name)
    return {
        "keep_core(≥10%)": sorted(keep_core),
        "keep_mid(3-10%)": sorted(keep_mid),
        "deprecate(<3%)": sorted(deprecate),
        "archive(0%)": sorted(archive),
    }


def render_md(user_stats: dict, cuts: dict, output: Path) -> None:
    lines = [
        "# W3 砍 / 留 决策矩阵(基于 100+ 用户数据)\n",
        f"\n## 用户画像\n",
        f"- 总数:{user_stats['total']}",
        f"- 行业 top:{user_stats['industries']}",
        f"- 团队规模:{user_stats['team_sizes']}",
        f"- 来源渠道:{user_stats['channels']}",
        f"\n## Skill 决策\n",
    ]
    for k, v in cuts.items():
        lines.append(f"\n### {k}({len(v)} 项)")
        lines.append("\n" + "\n".join(f"- {s}" for s in v) if v else "(空)")
    lines.append(
        "\n\n## 行动\n"
        "1. **keep_core**:文档加强 + demo gif + 教学视频\n"
        "2. **keep_mid**:不主推,留\n"
        "3. **deprecate**:30 天观察期;再无人用 → 转 archive\n"
        "4. **archive**:`marketplace/.archive/` 归档\n"
    )
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    workspace = Path(__file__).resolve().parents[1] / "workspace" / "学习"
    users_csv = workspace / "users-2026-05.csv"
    skills_csv = workspace / "skill-usage-2026-05.csv"
    out = workspace / "W3-cut-list.md"
    workspace.mkdir(parents=True, exist_ok=True)

    users = load_csv(users_csv)
    skills = load_csv(skills_csv)
    if not users or not skills:
        print("缺数据;请先跑 scripts/export-users.sql 出 csv", file=sys.stderr)
        return 1

    user_stats = analyze_users(users)
    cuts = cut_decision(skills)
    render_md(user_stats, cuts, out)
    print(f"决策矩阵 → {out}")
    print(f"keep_core: {len(cuts['keep_core(≥10%)'])} 项")
    print(f"deprecate: {len(cuts['deprecate(<3%)'])} 项")
    print(f"archive:   {len(cuts['archive(0%)'])} 项")
    return 0


if __name__ == "__main__":
    sys.exit(main())
