"""CI gate: 架构合规 + 路径硬编码检测.

检测内容:
1. 路径硬编码 — 应通过 settings 获取
2. 目录越界 — ai/ 下不应有业务 .py
3. 构建产物 — git tracked 中的残留

Exit 0 on pass, 1 on failure.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _git_tracked_files() -> set[str]:
    """获取 git 追踪的文件列表，自动排除 gitignored 的磁盘残留."""
    try:
        out = subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=PROJECT_ROOT, text=True, stderr=subprocess.DEVNULL,
        )
        return {line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()}
    except Exception:
        # 非 git 环境兜底
        return set()


def _is_tracked(rel_path: str, tracked: set[str]) -> bool:
    return rel_path.replace("\\", "/") in tracked


# ── 路径硬编码检测 ──────────────────────────────

FORBIDDEN_PATH_PATTERNS = [
    # Path("agents") / Path("skills") 等
    (r'Path\(["\']agents["\']\)', "应通过 get_settings().experts_dir"),
    (r'Path\(["\']skills["\']\)', "应通过 get_settings().skills_dir"),
    (r'Path\(["\']config["\']\)', "应通过 get_settings().config_dir"),
    # parents[2] / "agents" 等动态路径拼接
    (r'parents\[\d+\]\s*/\s*"agents"', "应通过 settings.experts_dir"),
    (r'parents\[\d+\]\s*/\s*"skills"', "应通过 settings.skills_dir"),
    (r'parents\[\d+\]\s*/\s*"config"', "应通过 settings.config_dir"),
    # Path.cwd() / "config"
    (r'Path\.cwd\(\)\s*/\s*"config"', "应通过 settings.config_dir"),
    # 裸字符串路径拼接（排除文档/测试中的字符串）
    (r'/ "agents"\b', "应通过 settings"),
    (r'/ "skills"\b', "应通过 settings"),
]

# 白名单：允许硬编码的合法文件
PATH_WHITELIST_FILES = {
    "install.py", "check_version_consistency.py",
    "check_hardcoded_values.py", "check_command_consistency.py",
    "analyze-usage.py", "check_arch_compliance.py",
}

# 白名单：不检查的目录前缀
PATH_WHITELIST_DIRS = (
    "ai/", "docs/", "scripts/", ".github/", "ci/",
    "workspace/", "examples/", "archive/",
)


def check_hardcoded_paths(tracked: set[str]) -> list[str]:
    """扫描 git tracked Python 文件中的路径硬编码."""
    errors: list[str] = []
    for rel_path in sorted(tracked):
        if not rel_path.endswith(".py"):
            continue
        rel = rel_path.replace("\\", "/")
        # 跳过白名单
        if Path(rel_path).name in PATH_WHITELIST_FILES:
            continue
        if rel.startswith(PATH_WHITELIST_DIRS):
            continue

        fp = PROJECT_ROOT / rel_path
        try:
            content = fp.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for pattern, desc in FORBIDDEN_PATH_PATTERNS:
            if re.search(pattern, content):
                # 允许 settings.py 自身的定义
                if "settings.py" in rel:
                    continue
                # 允许测试文件
                if "/tests/" in rel or rel.startswith("runtime/tests/"):
                    continue
                # 允许 docstring 中的说明（注释性路径）
                lines = content.split("\n")
                found_in_docstring = False
                for i, line in enumerate(lines):
                    if re.search(pattern, line):
                        # 简单的 docstring 检测
                        if '"""' in line or "'''" in line:
                            found_in_docstring = True
                        break
                if found_in_docstring:
                    continue
                errors.append(f"  {rel}: {desc}")
                break
    return errors


# ── 目录越界检测 ────────────────────────────────

def check_directory_purity(tracked: set[str]) -> list[str]:
    """检查各目录的纯净性."""
    errors: list[str] = []

    # ai/ 下不应有业务 .py（元skill自带脚本除外）
    ai_py = [f for f in tracked if f.startswith("ai/") and f.endswith(".py")]
    ai_whitelist = {"ai/skills/nuwa-skill/scripts/", "ai/skills/darwin-skill/scripts/"}
    ai_violations = [f for f in ai_py
                     if not any(f.startswith(w) for w in ai_whitelist)]
    if ai_violations:
        errors.append(f"  ai/ 业务 .py 越界: {len(ai_violations)} 个")
        for f in ai_violations[:5]:
            errors.append(f"    - {f}")

    # deploy/ 下不应有业务 .py（marketplace 脚本除外）
    deploy_py = [f for f in tracked if f.startswith("deploy/") and f.endswith(".py")]
    deploy_whitelist = {"deploy/marketplace/", "deploy/config/"}
    deploy_violations = [f for f in deploy_py
                         if not any(f.startswith(w) for w in deploy_whitelist)]
    if deploy_violations:
        errors.append(f"  deploy/ 业务 .py 越界: {len(deploy_violations)} 个")
        for f in deploy_violations[:5]:
            errors.append(f"    - {f}")

    # 根目录不应有多余的 .py（install.py 除外）
    root_allowed = {"install.py"}
    root_py = [f for f in tracked if "/" not in f and f.endswith(".py") and f not in root_allowed]
    if root_py:
        errors.append(f"  根目录多余 .py: {root_py}")

    return errors


# ── 构建产物检测 ──────────────────────────────────

BUILD_ARTIFACTS = [
    ("__pycache__", "Python缓存"),
    (".pytest_cache", "pytest缓存"),
    (".ruff_cache", "ruff缓存"),
    (".coverage", "覆盖率数据"),
    ("node_modules", "npm依赖"),
    ("*.tsbuildinfo", "TS编译信息"),
    ("*.log", "日志文件"),
    ("*.bak", "备份文件"),
]


def check_build_artifacts(tracked: set[str]) -> list[str]:
    """检查 git tracked 中是否有构建产物."""
    errors: list[str] = []
    for pattern, desc in BUILD_ARTIFACTS:
        if "*" in pattern:
            suffix = pattern[1:]
            matches = [f for f in tracked if f.endswith(suffix)]
        else:
            matches = [f for f in tracked
                       if f"/{pattern}/" in f"/{f}" or f == pattern]
        if matches:
            errors.append(f"  {desc}: {len(matches)} 个")
            for m in matches[:3]:
                errors.append(f"    - {m}")
    return errors


# ── Main ──────────────────────────────────────────

def main() -> int:
    tracked = _git_tracked_files()
    if not tracked:
        print("WARN: 非 git 环境，跳过 audit")
        return 0

    all_errors: list[str] = []

    print("=== 路径硬编码检测 ===")
    errs = check_hardcoded_paths(tracked)
    if errs:
        print(f"FAIL: {len(errs)} 处")
        all_errors.extend(errs)
        for e in errs:
            print(e)
    else:
        print("PASS")

    print("\n=== 目录纯净性 ===")
    errs = check_directory_purity(tracked)
    if errs:
        all_errors.extend(errs)
        for e in errs:
            print(e)
    else:
        print("PASS")

    print("\n=== 构建产物残留 ===")
    errs = check_build_artifacts(tracked)
    if errs:
        all_errors.extend(errs)
        for e in errs:
            print(e)
    else:
        print("PASS")

    if all_errors:
        print(f"\nFAIL: {len(all_errors)} 项不合规")
        return 1

    print("\nALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
