# SPDX-License-Identifier: MIT
# DEPRECATED: use a11y_scanner_v2 instead. This file will be removed in V1.2.
"""
无障碍 / Accessibility 测试（WCAG 2.1）
被引用方：UX / 易用性 / 合规

工具：
- axe-core（注入到 Playwright 页面）
- Lighthouse a11y category（外部）
- pa11y CLI（外部，npm install -g pa11y）
"""
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ===== axe-core via Playwright =====

def scan_with_axe(page, url: Optional[str] = None) -> Dict:
    """
    向 Playwright 页面注入 axe-core，扫描无障碍问题。
    page: Playwright Page 对象
    """
    if url:
        page.goto(url, wait_until="networkidle")
    page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js")
    result = page.evaluate("""
        () => new Promise(resolve => {
            axe.run((err, results) => {
                if (err) resolve({error: err.message});
                else resolve(results);
            });
        });
    """)

    violations = result.get("violations", [])
    by_impact = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for v in violations:
        impact = v.get("impact", "minor")
        by_impact[impact] = by_impact.get(impact, 0) + 1

    return {
        "url": page.url,
        "violations_count": len(violations),
        "by_impact": by_impact,
        "violations": [
            {
                "id": v["id"], "impact": v["impact"],
                "description": v["description"][:200],
                "help_url": v["helpUrl"],
                "nodes_count": len(v.get("nodes", [])),
            }
            for v in violations[:20]
        ],
    }


# ===== Lighthouse a11y =====

def scan_with_lighthouse(url: str, output_dir: str = None) -> Dict:
    if output_dir is None:
        output_dir = f"workspace/测试报告/{os.getenv('PROJECT_NAME', 'default')}/a11y"
    """需 npm install -g lighthouse"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    out_json = Path(output_dir) / "lighthouse_a11y.json"
    cmd = [
        "lighthouse", url,
        "--only-categories=accessibility",
        "--output=json",
        f"--output-path={out_json}",
        "--chrome-flags=--headless --no-sandbox",
        "--quiet",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        return {"error": proc.stderr[-500:]}
    data = json.loads(out_json.read_text(encoding="utf-8"))
    score = data.get("categories", {}).get("accessibility", {}).get("score", 0)
    audits = data.get("audits", {})
    failed = [k for k, v in audits.items()
              if v.get("score") is not None and v.get("score") < 1]
    return {
        "url": url,
        "a11y_score": round((score or 0) * 100, 1),
        "failed_audits": failed,
        "report": str(out_json),
    }


# ===== pa11y CLI =====

def scan_with_pa11y(url: str) -> Dict:
    """需 npm install -g pa11y"""
    cmd = ["pa11y", url, "--reporter", "json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    try:
        issues = json.loads(proc.stdout) if proc.stdout else []
    except json.JSONDecodeError:
        issues = []
    by_type = {}
    for i in issues:
        by_type[i.get("type", "other")] = by_type.get(i.get("type", "other"), 0) + 1
    return {"url": url, "total_issues": len(issues), "by_type": by_type}


# ===== WCAG 2.1 检查清单 =====

WCAG_CHECKLIST = """
A 级（必须）：
□ 1.1.1 非文本内容有 alt 描述
□ 1.3.1 信息和关系（语义化标签）
□ 1.4.1 颜色不作为唯一信息载体
□ 2.1.1 键盘可达
□ 2.4.4 链接目的明确
□ 3.1.1 页面 lang 属性
□ 4.1.2 名称、角色、值（ARIA）

AA 级（强烈推荐）：
□ 1.4.3 对比度 ≥ 4.5:1（普通文本）/ 3:1（大文本）
□ 1.4.5 文字的图像（避免）
□ 2.4.7 焦点可见
□ 3.3.1 错误识别
□ 4.1.3 状态消息（aria-live）

AAA 级（高级）：
□ 1.4.6 增强对比度 ≥ 7:1
□ 2.1.3 完全键盘可达（无超时）
"""


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="A11y 扫描")
    sub = parser.add_subparsers(dest="cmd")
    lh = sub.add_parser("lighthouse"); lh.add_argument("url")
    pa = sub.add_parser("pa11y"); pa.add_argument("url")
    cl = sub.add_parser("checklist")
    args = parser.parse_args()
    if args.cmd == "lighthouse":
        print(json.dumps(scan_with_lighthouse(args.url), indent=2, ensure_ascii=False))
    elif args.cmd == "pa11y":
        print(json.dumps(scan_with_pa11y(args.url), indent=2, ensure_ascii=False))
    elif args.cmd == "checklist":
        print(WCAG_CHECKLIST)
