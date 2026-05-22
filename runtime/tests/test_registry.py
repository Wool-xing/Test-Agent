"""Smoke test: registry scans existing experts + skills."""

from __future__ import annotations

import pathlib

from runtime.registry.registry import build_catalog

# 动态扫源目录而非写死数字 — 项目持续增长 agent/skill,基线会过时
_PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
_EXPERTS_DIR = _PROJECT_ROOT / "agents"
_SKILLS_DIR = _PROJECT_ROOT / "skills"


def test_catalog_loads_existing_assets():
    cat = build_catalog()

    # 业务 agent 文件: 排除 README,只数 [0-9]*.md
    src_experts = len(list(_EXPERTS_DIR.glob("[0-9]*.md")))
    # skill 文件: 排除 README,数顶层 *.md (上游派生子目录另算)
    src_skills = len(list(_SKILLS_DIR.glob("*.md"))) - 1  # -1 for README.md

    assert len(cat.experts) >= src_experts, (
        f"experts loaded={len(cat.experts)}, source agents={src_experts} "
        f"— registry 漏扫,检查 agents/ 下的 [0-9]*.md 文件"
    )
    assert len(cat.skills) >= src_skills, (
        f"skills loaded={len(cat.skills)}, source skills>={src_skills} "
        f"— registry 漏扫,检查 skills/ 下的 *.md 文件"
    )
    assert "test-lead" in cat.experts, "test-lead expert missing"


def test_catalog_entries_have_description():
    cat = build_catalog()
    for entry in cat.all():
        assert entry.description, f"{entry.name} missing description"


def test_lookup_returns_entry():
    cat = build_catalog()
    e = cat.lookup("test-lead")
    assert e is not None
    assert e.kind == "expert"
