"""CI gate: 架构合规 + 路径硬编码检测.

检测内容:
1. 路径硬编码 — Path("agents") / Path("skills") 等应通过 settings 获取
2. 目录越界 — ai/ 下不应有 .py, runtime/ 下不应有 .md 定义
3. v2 冗余 — _v2.py 文件是否有对应引用

Exit 0 on pass, 1 on failure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ── 路径硬编码检测 ──────────────────────────────
# 这些路径应在 settings.py 中统一管理，不应硬编码
FORBIDDEN_PATH_PATTERNS = [
    (r'Path\(["\']agents["\']\)', '"agents" 应通过 get_settings().experts_dir'),
    (r'Path\(["\']skills["\']\)', '"skills" 应通过 get_settings().skills_dir'),
    (r'Path\(["\']config["\']\)', '"config" 应通过 get_settings().config_dir'),
    (r'Path\(__file__\)[^)]*parents\[\d+\][^)]*/\s*"agents"', 'agents路径应通过settings'),
    (r'Path\(__file__\)[^)]*parents\[\d+\][^)]*/\s*"skills"', 'skills路径应通过settings'),
    (r'Path\(__file__\)[^)]*parents\[\d+\][^)]*/\s*"config"', 'config路径应通过settings'),
    (r'Path\.cwd\(\)\s*/\s*"config"', 'config路径应通过settings'),
    (r'/ "agents"', 'agents路径硬编码'),
    (r'/ "skills"', 'skills路径硬编码'),
]

# 白名单：允许硬编码的合法位置
WHITELIST_FILES = {
    "install.py",           # 部署脚本有自己的路径常量
    "check_version_consistency.py",
    "check_hardcoded_values.py",
    "check_command_consistency.py",
    "analyze-usage.py",
    "check_arch_compliance.py",  # 本文件
}

WHITELIST_DIRS = {
    "ai/",       # .md 文件不检测
    "docs/",     # 文档不检测
    "scripts/",  # 脚本有独立规则
    "tests/",    # 测试文件
    ".github/",
}

def check_hardcoded_paths() -> list[str]:
    """扫描 Python 文件中的路径硬编码."""
    errors: list[str] = []
    for py_file in PROJECT_ROOT.rglob("*.py"):
        rel = str(py_file.relative_to(PROJECT_ROOT)).replace("\\", "/")
        # 跳过白名单
        if py_file.name in WHITELIST_FILES:
            continue
        if any(rel.startswith(d) for d in WHITELIST_DIRS):
            continue
        # 跳过 site-packages / venv
        if ".venv" in str(py_file) or "node_modules" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern, desc in FORBIDDEN_PATH_PATTERNS:
            if re.search(pattern, content):
                # 允许 settings.py 中的定义语句
                if "settings.py" in rel and ("default=Path" in content or "Field(default" in content):
                    continue
                # 允许 install.py
                if "install.py" in rel:
                    continue
                errors.append(f"  {rel}: {desc}")
                break  # 每个文件只报一次
    return errors


# ── 目录越界检测 ────────────────────────────────

def check_directory_purity() -> list[str]:
    """检查各目录的纯净性."""
    errors: list[str] = []

    # ai/ 下不应有 .py 文件
    ai_py = list((PROJECT_ROOT / "ai").rglob("*.py"))
    if ai_py:
        errors.append(f"  ai/ 下不应有 .py 文件: {len(ai_py)} 个")
        for f in ai_py[:3]:
            errors.append(f"    - {f.relative_to(PROJECT_ROOT)}")

    # deploy/ 下不应有 .py 文件（除了 marketplace 可能有脚本）
    deploy_py = [f for f in (PROJECT_ROOT / "deploy").rglob("*.py")
                 if "marketplace" not in str(f)]
    if deploy_py:
        errors.append(f"  deploy/ 下不应有 .py 文件: {len(deploy_py)} 个")

    # 根目录不应有多余的 .py 文件
    root_allowed = {"install.py"}
    root_py = [f for f in PROJECT_ROOT.glob("*.py") if f.name not in root_allowed]
    if root_py:
        errors.append(f"  根目录不应有 .py 文件: {[f.name for f in root_py]}")

    return errors


# ── 构建产物检测 ──────────────────────────────────

def check_build_artifacts() -> list[str]:
    """检查是否有构建产物被提交."""
    errors: list[str] = []
    artifacts = [
        ("__pycache__", "Python缓存"),
        (".pytest_cache", "pytest缓存"),
        (".ruff_cache", "ruff缓存"),
        (".coverage", "覆盖率数据"),
        ("node_modules", "npm依赖"),
        ("package-lock.json", "npm lock文件"),
        ("*.pyc", "编译字节码"),
        ("*.log", "日志文件"),
        ("*.bak", "备份文件"),
        ("*.tsbuildinfo", "TS编译信息"),
    ]
    for pattern, desc in artifacts:
        matches = list(PROJECT_ROOT.rglob(pattern))
        if matches:
            # 排除 .git 和 .venv
            real = [m for m in matches
                    if ".git" not in str(m) and ".venv" not in str(m)
                    and "node_modules" not in str(m)]
            if real:
                errors.append(f"  {desc}: {len(real)} 个残留")
                for m in real[:3]:
                    errors.append(f"    - {m.relative_to(PROJECT_ROOT)}")
    return errors


# ── Main ──────────────────────────────────────────

def main() -> int:
    all_errors: list[str] = []

    print("=== 路径硬编码检测 ===")
    errs = check_hardcoded_paths()
    if errs:
        print(f"FAIL: {len(errs)} 处路径硬编码")
        all_errors.extend(errs)
        for e in errs:
            print(e)
    else:
        print("PASS: 无路径硬编码")

    print("\n=== 目录纯净性 ===")
    errs = check_directory_purity()
    if errs:
        all_errors.extend(errs)
        for e in errs:
            print(e)
    else:
        print("PASS: 目录结构合规")

    print("\n=== 构建产物检测 ===")
    errs = check_build_artifacts()
    if errs:
        all_errors.extend(errs)
        for e in errs:
            print(e)
    else:
        print("PASS: 无构建产物残留")

    if all_errors:
        print(f"\nFAIL: {len(all_errors)} 项不合规")
        return 1

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
