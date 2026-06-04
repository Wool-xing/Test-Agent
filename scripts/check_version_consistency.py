"""版本号一致性检查 — pre-commit hook。

读取项目根 VERSION 文件，扫描所有声明版本的代码文件，
任一声明与 VERSION 不匹配 → 报错并列出差异。

用法:
    python scripts/check_version_consistency.py    # 检查所有文件
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Windows GBK 终端兼容
if sys.stdout.encoding.upper() != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_version() -> str:
    vf = PROJECT_ROOT / "VERSION"
    if not vf.is_file():
        print("ERROR: VERSION file not found")
        sys.exit(1)
    return vf.read_text(encoding="utf-8").strip()


# 文件 → 提取版本号的方式
#   pattern: 正则，第一个捕获组是版本号
#   format:  "raw" → 直接比对 / "v-prefix" → 比对时去掉 v 前缀
CHECKS: list[dict] = [
    # --- package.json ---
    {"path": "desktop/package.json", "key": '"version"', "pattern": r'"version"\s*:\s*"([^"]+)"'},
    {"path": "mobile/package.json", "key": '"version"', "pattern": r'"version"\s*:\s*"([^"]+)"'},
    {"path": "runtime/web/package.json", "key": '"version"', "pattern": r'"version"\s*:\s*"([^"]+)"'},
    # --- pyproject.toml ---
    {"path": "runtime/pyproject.toml", "key": "version =", "pattern": r'version\s*=\s*"([^"]+)"'},
    # --- TypeScript/TSX: getAppVersion / 显示版本 ---
    {"path": "desktop/electron/preload.ts", "key": "getAppVersion",
     "pattern": r'getAppVersion:\s*\(\)\s*=>\s*"([^"]+)"'},
    {"path": "desktop/electron/preload_extended.ts", "key": "getAppVersion",
     "pattern": r'getAppVersion:\s*\(\)\s*=>\s*"([^"]+)"'},
    {"path": "runtime/web/src/App.tsx", "key": "vX.Y.Z display",
     "pattern": r'v(\d+\.\d+\.\d+)', "format": "v-prefix"},
    {"path": "runtime/web/src/pages/FeedbackPage.tsx", "key": "Desktop vX.Y.Z",
     "pattern": r'Test-Agent Desktop v(\d+\.\d+\.\d+)', "format": "v-prefix"},
    # --- Python: 硬编码版本 ---
    {"path": "utils/reporting/evidence_chain.py", "key": 'fallback "1.0.0"',
     "pattern": r'else\s+"(\d+\.\d+\.\d+)"'},
    {"path": "utils/trackers/zentao_bug_manager.py", "key": 'fallback "1.0.0"',
     "pattern": r'else\s+"(\d+\.\d+\.\d+)"'},
    # --- 文档: FULL_GUIDE 版本行 ---
    {"path": "FULL_GUIDE.md", "key": "版本：V",
     "pattern": r'\*\*版本\*\*：V(\d+\.\d+\.\d+)', "format": "v-prefix"},
    {"path": "ROADMAP.md", "key": "当前状态:V",
     "pattern": r'当前状态:V(\d+\.\d+\.\d+)', "format": "v-prefix"},
    {"path": "agents/01-测试主管.md", "key": "实装状态 V",
     "pattern": r'\*\*V(\d+\.\d+\.\d+)\s+实装', "format": "v-prefix"},
    # --- 文档: INDEX / 标题 ---
    {"path": "runtime/web/INDEX.md", "key": "标题",
     "pattern": r'#\s+runtime/web\s+索引\s*[\(（]V?(\d+\.\d+\.\d+)', "format": "v-prefix"},
    {"path": "config/llm-providers.md", "key": "实测有效",
     "pattern": r'实测有效\*\*\s*[\(（]V?(\d+\.\d+\.\d+)', "format": "v-prefix"},
    {"path": "config/templates/INDEX.md", "key": "标题",
     "pattern": r'#\s+配置模板库索引[（(]V?(\d+\.\d+\.\d+)', "format": "v-prefix"},
]


def _check_file(entry: dict, expected: str) -> str | None:
    """检查单个文件，返回错误描述或 None。"""
    fpath = PROJECT_ROOT / entry["path"]
    if not fpath.is_file():
        return f"  文件不存在: {entry['path']}"

    content = fpath.read_text(encoding="utf-8", errors="ignore")
    m = re.search(entry["pattern"], content)
    if not m:
        return f"  未找到 {entry['key']} 声明: {entry['path']}"

    found = m.group(1)
    fmt = entry.get("format", "raw")

    if fmt == "v-prefix":
        # VERSION 是 "1.0.0"，文件中可能是 "v1.0.0"
        if found != expected:
            return f"  {entry['path']}: v{found} (期望 v{expected})"
    else:
        if found != expected:
            return f"  {entry['path']}: {found} (期望 {expected})"
    return None


def main() -> int:
    expected = _read_version()
    print(f"VERSION = {expected}")
    errors: list[str] = []

    for entry in CHECKS:
        err = _check_file(entry, expected)
        if err:
            errors.append(err)

    if errors:
        print(f"\nFAIL: version mismatch ({len(errors)} location(s)):\n")
        for e in errors:
            print(e)
        print(f"\nFix: update all files above to version {expected}")
        return 1

    print(f"OK: all {len(CHECKS)} version locations consistent ({expected})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
