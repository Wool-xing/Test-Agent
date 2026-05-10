# SPDX-License-Identifier: MIT
"""
OpenAPI / Swagger 自动用例生成（Schemathesis 风格）
被引用方：API 测试 / 契约 / 模糊测试

依赖：pip install schemathesis（生产用）；本文件提供轻量替代
"""
import json
import logging
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


def load_openapi_spec(path_or_url: str) -> Dict:
    """从文件 / URL 加载 OpenAPI / Swagger 规范"""
    if path_or_url.startswith(("http://", "https://")):
        r = requests.get(path_or_url, timeout=10)
        r.raise_for_status()
        text = r.text
    else:
        text = Path(path_or_url).read_text(encoding="utf-8")
    if path_or_url.endswith(".yaml") or path_or_url.endswith(".yml") or text.lstrip().startswith("openapi"):
        return yaml.safe_load(text)
    return json.loads(text)


def generate_test_cases(spec: Dict, base_url: str,
                        output: str = "workspace/测试用例/openapi_cases.json") -> str:
    """
    遍历 OpenAPI paths，每个 endpoint × method 生成 1 用例。
    """
    cases: List[Dict] = []
    for path, ops in spec.get("paths", {}).items():
        for method, details in ops.items():
            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                continue
            cases.append({
                "id": f"TC-API-{method.upper()}-{path.replace('/', '_').strip('_')}",
                "type": "API",
                "method": method.upper(),
                "path": path,
                "url": base_url.rstrip("/") + path,
                "summary": details.get("summary", ""),
                "operation_id": details.get("operationId"),
                "expected_status": list((details.get("responses") or {"200": {}}).keys())[0],
                "tags": details.get("tags", []),
            })

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(cases, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"OpenAPI 自动生成 {len(cases)} 用例 → {output}")
    return output


def smoke_test_all_endpoints(spec: Dict, base_url: str,
                              auth_header: Optional[str] = None,
                              skip_destructive: bool = True) -> Dict:
    """
    冒烟扫所有 endpoint：可达性 + 状态码合理性。
    skip_destructive=True 跳过 DELETE/PUT/POST，仅 GET/HEAD。
    """
    headers = {"Authorization": auth_header} if auth_header else {}
    results = {"total": 0, "passed": 0, "failed": 0, "details": []}

    for path, ops in spec.get("paths", {}).items():
        for method in ops:
            m = method.upper()
            if skip_destructive and m not in ("GET", "HEAD"):
                continue
            url = base_url.rstrip("/") + path
            results["total"] += 1
            try:
                # path 中含 {id} 等占位符简单替换
                url_resolved = url.replace("{id}", "1").replace("{userId}", "1")
                r = requests.request(m, url_resolved, headers=headers, timeout=10)
                ok = r.status_code < 500
                if ok:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                results["details"].append({
                    "method": m, "path": path, "status": r.status_code, "ok": ok,
                })
            except Exception as e:
                results["failed"] += 1
                results["details"].append({"method": m, "path": path, "error": str(e)})
    return results


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="OpenAPI 用例生成 + 冒烟")
    sub = parser.add_subparsers(dest="cmd")
    g = sub.add_parser("gen"); g.add_argument("spec"); g.add_argument("--base-url", required=True)
    s = sub.add_parser("smoke"); s.add_argument("spec"); s.add_argument("--base-url", required=True); s.add_argument("--auth", default=None)
    args = parser.parse_args()
    spec = load_openapi_spec(args.spec)
    if args.cmd == "gen":
        generate_test_cases(spec, args.base_url)
    elif args.cmd == "smoke":
        print(json.dumps(smoke_test_all_endpoints(spec, args.base_url, args.auth),
                          indent=2, ensure_ascii=False))
