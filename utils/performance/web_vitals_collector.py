# SPDX-License-Identifier: MIT
"""
前端性能 Web Vitals 采集（LCP / FID / CLS / FCP / TTFB）
被引用方：06-自动化脚本 / Web 测试场景

实现：
- 用 Playwright 注入 web-vitals.js（CDN）
- 或调 Lighthouse CLI（外部，性能更准）
"""
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


# Google 推荐阈值（Core Web Vitals）
WEB_VITALS_THRESHOLDS = {
    "LCP_ms":       {"good": 2500, "poor": 4000},
    "FID_ms":       {"good": 100,  "poor": 300},
    "CLS":          {"good": 0.1,  "poor": 0.25},
    "FCP_ms":       {"good": 1800, "poor": 3000},
    "TTFB_ms":      {"good": 800,  "poor": 1800},
    "INP_ms":       {"good": 200,  "poor": 500},
}


# ===== 方式 1：Playwright 注入 web-vitals.js =====

def collect_via_playwright(url: str, page=None, timeout: int = 30) -> Dict:
    """
    用 Playwright 打开 URL，注入 web-vitals 库收集指标。
    page: 可传入已有 Playwright Page；不传则新建。
    """
    if page is None:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        owns = (pw, browser)
    else:
        owns = None

    try:
        page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
        # 注入 web-vitals
        page.add_script_tag(url="https://unpkg.com/web-vitals@3/dist/web-vitals.iife.js")
        # 等待用户交互（FID 需要）—— 模拟点击 body 触发
        page.evaluate("document.body.click()")
        page.wait_for_timeout(2000)
        metrics = page.evaluate("""
            () => new Promise(resolve => {
                const m = {};
                webVitals.onLCP(v => { m.LCP = v.value; check(); });
                webVitals.onFID(v => { m.FID = v.value; check(); });
                webVitals.onCLS(v => { m.CLS = v.value; check(); });
                webVitals.onFCP(v => { m.FCP = v.value; check(); });
                webVitals.onTTFB(v => { m.TTFB = v.value; check(); });
                webVitals.onINP(v => { m.INP = v.value; check(); });
                function check() {
                    if (Object.keys(m).length >= 4) resolve(m);
                }
                setTimeout(() => resolve(m), 8000);
            });
        """)
        return {
            "url": url,
            "LCP_ms":  round(metrics.get("LCP", 0)),
            "FID_ms":  round(metrics.get("FID", 0)),
            "CLS":     round(metrics.get("CLS", 0), 3),
            "FCP_ms":  round(metrics.get("FCP", 0)),
            "TTFB_ms": round(metrics.get("TTFB", 0)),
            "INP_ms":  round(metrics.get("INP", 0)) if metrics.get("INP") else None,
        }
    finally:
        if owns:
            owns[1].close()
            owns[0].stop()


# ===== 方式 2：Lighthouse CLI（更权威）=====

def collect_via_lighthouse(url: str, output_dir: str = "workspace/测试报告/web-vitals") -> Dict:
    """需安装 lighthouse: npm install -g lighthouse"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    json_path = Path(output_dir) / "lighthouse.json"

    cmd = [
        "lighthouse", url,
        "--output=json",
        f"--output-path={json_path}",
        "--chrome-flags=--headless --no-sandbox",
        "--quiet",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if proc.returncode != 0:
        logger.error(f"lighthouse 失败: {proc.stderr}")
        return {"error": proc.stderr}

    data = json.loads(json_path.read_text(encoding="utf-8"))
    audits = data.get("audits", {})
    return {
        "url": url,
        "LCP_ms":  round(audits.get("largest-contentful-paint", {}).get("numericValue", 0)),
        "FCP_ms":  round(audits.get("first-contentful-paint", {}).get("numericValue", 0)),
        "TTFB_ms": round(audits.get("server-response-time", {}).get("numericValue", 0)),
        "CLS":     round(audits.get("cumulative-layout-shift", {}).get("numericValue", 0), 3),
        "TBT_ms":  round(audits.get("total-blocking-time", {}).get("numericValue", 0)),
        "performance_score": data.get("categories", {}).get("performance", {}).get("score"),
    }


# ===== 门禁判定 =====

def check_vitals_gates(metrics: Dict) -> Dict:
    results = {}
    for k, thresh in WEB_VITALS_THRESHOLDS.items():
        v = metrics.get(k)
        if v is None:
            continue
        if v <= thresh["good"]:
            results[k] = {"value": v, "status": "good"}
        elif v <= thresh["poor"]:
            results[k] = {"value": v, "status": "needs_improvement"}
        else:
            results[k] = {"value": v, "status": "poor"}
    return results


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Web Vitals 采集")
    parser.add_argument("url")
    parser.add_argument("--method", choices=["playwright", "lighthouse"], default="playwright")
    args = parser.parse_args()
    if args.method == "lighthouse":
        m = collect_via_lighthouse(args.url)
    else:
        m = collect_via_playwright(args.url)
    print(json.dumps({"metrics": m, "gates": check_vitals_gates(m)}, indent=2, ensure_ascii=False))
