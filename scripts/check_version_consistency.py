"""版本号一致性检查 — pre-commit hook + CI。

双层防御：
  1. 动态扫描 — 全局搜所有 package.json / pyproject.toml / .tsx 中的版本声明
  2. 显式检查 — 已知关键位置精确匹配

任一声明 != VERSION → 报错，阻止提交。

用法:
    python scripts/check_version_consistency.py           # 本地检查
    python scripts/check_version_consistency.py --ci      # CI 模式(GitHub Actions)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Windows GBK → UTF-8
if sys.stdout.encoding.upper() != "UTF-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"node_modules", ".git", ".venv", "__pycache__", ".egg-info",
             "workspace", "archive", "dist", "out", ".claude-crap"}


def _read_version() -> str:
    vf = PROJECT_ROOT / "VERSION"
    if not vf.is_file():
        print("ERROR: VERSION file not found")
        sys.exit(1)
    return vf.read_text(encoding="utf-8").strip()


# ── Layer 1: Dynamic scan ──────────────────────────────────────────

def _scan_package_json(expected: str) -> list[str]:
    """Scan ALL package.json files (recursive) for version field."""
    errors: list[str] = []
    for f in PROJECT_ROOT.rglob("package.json"):
        if any(skip in f.parts for skip in SKIP_DIRS):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'"version"\s*:\s*"([^"]+)"', content)
            if m and m.group(1) != expected:
                rel = f.relative_to(PROJECT_ROOT)
                errors.append(f"  {rel}: {m.group(1)} (expected {expected})")
        except Exception:
            pass
    return errors


def _scan_pyproject_toml(expected: str) -> list[str]:
    """Scan ALL pyproject.toml files for project version."""
    errors: list[str] = []
    for f in PROJECT_ROOT.rglob("pyproject.toml"):
        if any(skip in f.parts for skip in SKIP_DIRS):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'\nversion\s*=\s*"([^"]+)"', content)
            if m and m.group(1) != expected:
                rel = f.relative_to(PROJECT_ROOT)
                errors.append(f"  {rel}: {m.group(1)} (expected {expected})")
        except Exception:
            pass
    return errors


def _scan_tsx_ts(expected: str) -> list[str]:
    """Scan TypeScript/TSX files for getAppVersion() or vX.Y.Z display strings."""
    errors: list[str] = []
    patterns = [
        (r'export const APP_VERSION\s*=\s*"([^"]+)"', "APP_VERSION constant"),
        (r'getAppVersion\s*:\s*\(\)\s*=>\s*"([^"]+)"', "getAppVersion"),
        (r"Test-Agent\s+(?:Desktop\s+)?v(\d+\.\d+\.\d+)", "display"),
    ]
    search_dirs = [
        PROJECT_ROOT / "desktop",
        PROJECT_ROOT / "runtime" / "web" / "src",
    ]
    for sd in search_dirs:
        if not sd.is_dir():
            continue
        for f in sd.rglob("*"):
            if f.suffix not in (".ts", ".tsx"):
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                for pat, label in patterns:
                    for m in re.finditer(pat, content):
                        if m.group(1) != expected:
                            rel = f.relative_to(PROJECT_ROOT)
                            errors.append(f"  {rel}: v{m.group(1)} [{label}] (expected v{expected})")
            except Exception:
                pass
    return errors


# ── Layer 2: Explicit checks (key document headers) ─────────────────

def _check_doc_versions(expected: str) -> list[str]:
    """Check active documentation files for version references."""
    errors: list[str] = []
    checks = [
        ("FULL_GUIDE.md", r'\*\*版本\*\*：V(\d+\.\d+\.\d+)'),
        ("ROADMAP.md", r'当前状态:V(\d+\.\d+\.\d+)'),
        ("agents/01-测试主管.md", r'\*\*V(\d+\.\d+\.\d+)\s+实装'),
        ("config/llm-providers.md", r'实测有效\*\*\s*[\(（]V?(\d+\.\d+\.\d+)'),
        ("config/templates/INDEX.md", r'#\s+配置模板库索引[（(]V?(\d+\.\d+\.\d+)'),
        ("runtime/web/INDEX.md", r'#\s+runtime/web\s+索引\s*[\(（]V?(\d+\.\d+\.\d+)'),
    ]
    for path, pattern in checks:
        f = PROJECT_ROOT / path
        if not f.is_file():
            errors.append(f"  {path}: file not found")
            continue
        content = f.read_text(encoding="utf-8", errors="ignore")
        m = re.search(pattern, content)
        if m and m.group(1) != expected:
            errors.append(f"  {path}: V{m.group(1)} (expected V{expected})")
    return errors


# ── Main ────────────────────────────────────────────────────────────

def main() -> int:
    expected = _read_version()
    all_errors: list[str] = []

    print(f"VERSION = {expected}")

    # Layer 1: Dynamic scan
    all_errors.extend(_scan_package_json(expected))
    all_errors.extend(_scan_pyproject_toml(expected))
    all_errors.extend(_scan_tsx_ts(expected))

    # Layer 2: Explicit doc checks
    all_errors.extend(_check_doc_versions(expected))

    scanned = 4  # 4 scan categories

    if all_errors:
        print(f"\nFAIL: {len(all_errors)} version mismatch(es) found across {scanned} scan categories:\n")
        for e in all_errors:
            print(e)
        print(f"\nFix: update all files above to version {expected}")
        print("If a file is tracking a DIFFERENT project/package version, add it to SKIP_DIRS or open an issue.")
        return 1

    print(f"OK: all scanned locations consistent ({expected})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
