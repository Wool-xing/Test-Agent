# SPDX-License-Identifier: MIT
"""
禅道 Bug 管理客户端 - 使用指数退避重试
权威 severity 映射：1=P0, 2=P1, 3=P2, 4=P3
"""
import logging
import os
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

# 同包 import（部署后 utils/ 在 sys.path 中）
from api_retry_util import call_with_retry

load_dotenv()
logger = logging.getLogger(__name__)


# severity / pri 权威映射
SEVERITY_MAP = {"P0": 1, "P1": 2, "P2": 3, "P3": 4}
# pri 与 severity 同表（项目可在此处按禅道流程自定义）
PRI_MAP = {"P0": 1, "P1": 2, "P2": 3, "P3": 4}


class ZentaoBugManager:
    """禅道 Bug 管理客户端，所有 API 调用自动重试（指数退避）"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        account: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.base_url = (
            base_url
            or os.getenv("TEST_ZENTAO_URL")
            or os.getenv("ZENTAO_BASE_URL", "")
        ).rstrip("/")
        self.account = account or os.getenv("ZENTAO_ACCOUNT", "")
        self.password = password or os.getenv("ZENTAO_PASSWORD", "")
        self.session = requests.Session()
        self.token: Optional[str] = None
        if not self.base_url:
            raise ValueError("ZENTAO_BASE_URL 未配置；请在 .env 设置 ZENTAO_BASE_URL 或 TEST_ZENTAO_URL")
        self._login()

    def _login(self):
        """登录禅道获取 Token（带重试）。token 失效后调用本方法续期。"""
        resp = call_with_retry(
            self.session.post,
            f"{self.base_url}/tokens",
            json={"account": self.account, "password": self.password},
            max_retries=3,
            base_delay=5.0,
            retryable_status_codes=(429, 500, 502, 503, 504),
        )
        resp.raise_for_status()
        body = resp.json()
        self.token = body.get("token")
        if not self.token:
            raise RuntimeError(f"禅道登录响应无 token 字段: {body}")
        # 禅道 v18+ 用 Token header；项目按需改 Authorization Bearer
        self.session.headers.update({"Token": self.token})
        logger.info("禅道登录成功")

    def _request(self, method: str, path: str, _retry_on_401: bool = True, **kwargs) -> dict:
        """通用请求（重试 + 401 自动续期）"""
        try:
            resp = call_with_retry(
                self.session.request,
                method,
                f"{self.base_url}{path}",
                max_retries=3,
                base_delay=10.0,
                max_delay=60.0,
                retryable_status_codes=(429, 500, 502, 503, 504),
                **kwargs,
            )
        except requests.exceptions.HTTPError as e:
            # 401 token 失效，重登一次再试
            if _retry_on_401 and e.response is not None and e.response.status_code == 401:
                logger.warning("Token 失效，自动重新登录")
                self._login()
                return self._request(method, path, _retry_on_401=False, **kwargs)
            raise
        resp.raise_for_status()
        return resp.json()

    def create_bug(self, bug_data: Dict) -> Dict:
        """
        提交 Bug 到禅道。
        必填：title, product, steps, severity (1=P0..4=P3)
        可选：module, project, assignedTo, pri, type, os, browser, buildFound, keywords
        """
        for f in ("title", "product", "steps"):
            if f not in bug_data:
                raise ValueError(f"Bug 数据缺少必填字段：{f}")

        defaults = {
            "severity": 3,
            "pri": 3,
            "type": "codeerror",
            "os": "All",
            "browser": "All",
        }
        payload = {**defaults, **bug_data}
        result = self._request("POST", "/bugs", json=payload)

        if not result.get("id"):
            logger.error(f"禅道返回无 id 字段，可能 API 兼容性问题: {result}")
        else:
            logger.info(f"Bug 提交成功：#{result['id']} - {bug_data['title']}")
        return result

    def get_bug(self, bug_id: int) -> Dict:
        return self._request("GET", f"/bugs/{bug_id}")

    def update_bug(self, bug_id: int, update_data: Dict) -> Dict:
        result = self._request("PUT", f"/bugs/{bug_id}", json=update_data)
        logger.info(f"Bug#{bug_id} 已更新")
        return result

    def close_bug(self, bug_id: int, resolution: str = "fixed") -> Dict:
        return self.update_bug(bug_id, {"status": "closed", "resolution": resolution})

    def reopen_bug(self, bug_id: int, comment: str = "") -> Dict:
        return self.update_bug(bug_id, {
            "status": "active",
            "comment": comment or "回归验证失败，重新打开",
        })

    def list_bugs(
        self,
        product_id: int,
        status: str = "active",
        severity: Optional[int] = None,
        page: int = 1,
        limit: int = 50,
    ) -> List[Dict]:
        """查询 Bug 列表。severity 用 1-4 数值（与权威映射一致）。"""
        params = {"product": product_id, "status": status, "page": page, "limit": limit}
        if severity is not None:
            params["severity"] = severity
        result = self._request("GET", "/bugs", params=params)
        return result.get("bugs", [])

    def get_bug_stats(self, product_id: int) -> Dict:
        bugs = self.list_bugs(product_id, status="active", limit=200)
        stats = {"P0": 0, "P1": 0, "P2": 0, "P3": 0, "total": len(bugs)}
        rev_map = {1: "P0", 2: "P1", 3: "P2", 4: "P3"}
        for bug in bugs:
            level = rev_map.get(bug.get("severity", 3), "P2")
            stats[level] += 1
        return stats

    def batch_submit_from_failures(
        self,
        failures: List[Dict],
        product_id: int,
        build_version: str,
    ) -> List[Dict]:
        """
        从测试失败列表批量提交 Bug。
        failure 字段：case_id, case_name, priority(P0..P3), steps, module, failure_type
        仅 failure_type == 'product_bug' 提交。
        """
        results = []
        for failure in failures:
            if failure.get("failure_type") != "product_bug":
                continue
            priority = failure.get("priority", "P2")
            bug_data = {
                "title": f"{failure.get('module', '未知模块')}-{failure.get('case_name', '')}",
                "product": product_id,
                "steps": failure.get("steps", "详见测试日志"),
                "severity": SEVERITY_MAP.get(priority, 3),
                "pri": PRI_MAP.get(priority, 3),
                "buildFound": build_version,
                "keywords": failure.get("case_id", ""),
            }
            try:
                r = self.create_bug(bug_data)
                results.append({
                    "case_id": failure.get("case_id"),
                    "bug_id": r.get("id"),
                    "priority": priority,
                    "status": "submitted",
                })
            except Exception as e:
                logger.error(f"Bug 提交失败：{failure.get('case_id')} - {e}")
                results.append({
                    "case_id": failure.get("case_id"),
                    "bug_id": None,
                    "priority": priority,
                    "status": "failed",
                    "error": str(e),
                })
        return results


# ===== 示例 =====

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    manager = ZentaoBugManager()

    bug = manager.create_bug({
        "title": "登录模块-正确密码登录后跳转到404页面",
        "product": 1,
        "steps": (
            "**复现步骤：**\n"
            "1. 打开登录页\n"
            "2. 输入正确账号密码\n"
            "3. 点击登录\n\n"
            "**预期：** 跳转首页\n"
            "**实际：** 显示 404"
        ),
        "severity": SEVERITY_MAP["P0"],
        "pri": PRI_MAP["P0"],
        "assignedTo": "frontend-lead",
        "buildFound": "v1.0.0-rc1",
    })
    print(f"Bug 已提交：#{bug.get('id')}")
    stats = manager.get_bug_stats(product_id=1)
    print(f"当前活跃 Bug：{stats}")
