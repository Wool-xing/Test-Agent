# SPDX-License-Identifier: MIT
"""GitHub Issues Bug 管理客户端 — BugTrackerBase 适配器。

环境变量:
  GITHUB_TOKEN   — GitHub Personal Access Token
  GITHUB_REPO    — owner/repo (如 Wool-xing/Test-Agent)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests

try:
    from bug_tracker_base import BugTrackerBase, TRACKER_REGISTRY
except ImportError:
    from utils.trackers.bug_tracker_base import BugTrackerBase, TRACKER_REGISTRY

logger = logging.getLogger(__name__)

LABEL_BY_SEVERITY: dict[int, str] = {
    1: "P0-critical",
    2: "P1-high",
    3: "P2-medium",
    4: "P3-low",
}


class GitHubBugManager(BugTrackerBase):
    def __init__(
        self,
        token: str | None = None,
        repo: str | None = None,
    ):
        self.token = token or os.getenv("TAGENT_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN", "")
        self.repo = repo or os.getenv("TAGENT_GITHUB_REPO") or os.getenv("GITHUB_REPO", "")
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        if not self.token:
            raise ValueError("GITHUB_TOKEN 未配置")
        if not self.repo:
            raise ValueError("GITHUB_REPO 未配置 (格式: owner/repo)")

    @property
    def _api_base(self) -> str:
        return f"https://api.github.com/repos/{self.repo}"

    def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any] | list[dict[str, Any]]:
        url = (
            path if path.startswith("https://") else f"{self._api_base}{path}"
        )
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.text else {}

    def submit_bug(
        self,
        title: str,
        description: str,
        severity: int,
        attachments: list[str] | None = None,
        reproduce_steps: str = "",
    ) -> str:
        body = description
        if reproduce_steps:
            body += f"\n\n## 复现步骤\n{reproduce_steps}"
        label = LABEL_BY_SEVERITY.get(severity, "P2-medium")
        payload: dict[str, Any] = {
            "title": title,
            "body": body,
            "labels": ["bug", label],
        }
        result = self._request("POST", "/issues", json=payload)
        if isinstance(result, list):
            result = result[0] if result else {}
        number = result.get("number", 0)
        logger.info("GitHub Issue 已创建: #%s — %s", number, title)
        return str(number)

    def get_status(self, bug_id: str) -> dict[str, Any]:
        result = self._request("GET", f"/issues/{bug_id}")
        if isinstance(result, list):
            result = result[0] if result else {}
        labels = [lb.get("name", "") for lb in result.get("labels", [])]
        sev = 3
        for lb in labels:
            if lb.startswith("P") and "-" in lb:
                try:
                    sev = int(lb[1])
                except ValueError:
                    pass
        return {
            "status": result.get("state", "unknown"),
            "assignee": (
                (result.get("assignee", {}) or {}).get("login", "")
            ),
            "severity": sev,
            "last_updated": result.get("updated_at", ""),
        }

    def add_comment(
        self, bug_id: str, comment: str, attachments: list[str] | None = None
    ) -> None:
        self._request("POST", f"/issues/{bug_id}/comments", json={"body": comment})
        logger.info("GitHub Issue #%s: 已添加评论", bug_id)

    def link_testcase(self, bug_id: str, testcase_id: str) -> None:
        body = f"关联测试用例: `{testcase_id}`"
        self._request("POST", f"/issues/{bug_id}/comments", json={"body": body})

    def query_open_bugs(
        self, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"state": "open", "labels": "bug", "per_page": 100}
        if filters and "severity" in filters:
            params["labels"] = f"bug,{LABEL_BY_SEVERITY.get(filters['severity'], '')}"
        if filters and "assignee" in filters:
            params["assignee"] = filters["assignee"]
        result = self._request("GET", "/issues", params=params)
        if not isinstance(result, list):
            result = []
        issues: list[dict[str, Any]] = []
        for issue in result:
            labels = [lb.get("name", "") for lb in issue.get("labels", [])]
            sev = 3
            for lb in labels:
                if lb.startswith("P") and "-" in lb:
                    try:
                        sev = int(lb[1])
                    except ValueError:
                        pass
            issues.append({
                "bug_id": str(issue.get("number", "")),
                "title": issue.get("title", ""),
                "status": issue.get("state", ""),
                "severity": sev,
            })
        return issues


TRACKER_REGISTRY["github"] = GitHubBugManager
