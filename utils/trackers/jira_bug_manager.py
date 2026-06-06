# SPDX-License-Identifier: MIT
"""Jira Bug 管理客户端 — BugTrackerBase 适配器。

环境变量:
  JIRA_URL        — Jira 实例 URL (https://your-domain.atlassian.net)
  JIRA_EMAIL      — 登录邮箱
  JIRA_API_TOKEN  — Atlassian API Token
  JIRA_PROJECT    — 默认项目 KEY (如 PROJ)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv

from utils.trackers.bug_tracker_base import BugTrackerBase, TRACKER_REGISTRY

load_dotenv()
logger = logging.getLogger(__name__)

SEVERITY_MAP: dict[int, str] = {
    1: "Highest",
    2: "High",
    3: "Medium",
    4: "Low",
}


class JiraBugManager(BugTrackerBase):
    def __init__(
        self,
        url: str | None = None,
        email: str | None = None,
        api_token: str | None = None,
        project: str | None = None,
    ):
        self.url = (url or os.getenv("JIRA_URL", "")).rstrip("/")
        self.email = email or os.getenv("JIRA_EMAIL", "")
        self.api_token = api_token or os.getenv("JIRA_API_TOKEN", "")
        self.project = project or os.getenv("JIRA_PROJECT", "")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.session.auth = (self.email, self.api_token)

        if not self.url:
            raise ValueError("JIRA_URL 未配置")
        if not self.project:
            raise ValueError("JIRA_PROJECT 未配置")

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        resp = self.session.request(method, f"{self.url}/rest/api/3{path}", **kwargs)
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
        body = _build_description(description, reproduce_steps)
        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": self.project},
                "summary": title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": body}],
                        }
                    ],
                },
                "issuetype": {"name": "Bug"},
                "priority": {"name": SEVERITY_MAP.get(severity, "Medium")},
            }
        }
        result = self._request("POST", "/issue", json=payload)
        key: str = result.get("key", "")
        logger.info("Jira Bug 已创建: %s — %s", key, title)
        return key

    def get_status(self, bug_id: str) -> dict[str, Any]:
        result = self._request("GET", f"/issue/{bug_id}")
        fields = result.get("fields", {})
        return {
            "status": fields.get("status", {}).get("name", "unknown"),
            "assignee": (
                fields.get("assignee", {}) or {}
            ).get("displayName", ""),
            "severity": int(
                _reverse_priority(
                    (fields.get("priority", {}) or {}).get("name", "Medium")
                )
            ),
            "last_updated": fields.get("updated", ""),
        }

    def add_comment(
        self, bug_id: str, comment: str, attachments: list[str] | None = None
    ) -> None:
        self._request("POST", f"/issue/{bug_id}/comment", json={"body": comment})
        logger.info("Jira Bug %s: 已添加评论", bug_id)

    def link_testcase(self, bug_id: str, testcase_id: str) -> None:
        self._request(
            "POST",
            f"/issue/{bug_id}/remotelink",
            json={
                "object": {
                    "url": f"testcase://{testcase_id}",
                    "title": f"TestCase {testcase_id}",
                }
            },
        )

    def query_open_bugs(
        self, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        jql = f"project = {self.project} AND status != Closed"
        if filters:
            if "severity" in filters:
                name = SEVERITY_MAP.get(filters["severity"], "")
                if name:
                    jql += f' AND priority = "{name}"'
            if "assignee" in filters:
                jql += f' AND assignee = "{filters["assignee"]}"'
        result = self._request("GET", "/search", params={"jql": jql, "maxResults": 100})
        issues: list[dict[str, Any]] = []
        for issue in result.get("issues", []):
            f = issue.get("fields", {})
            issues.append({
                "bug_id": issue.get("key", ""),
                "title": f.get("summary", ""),
                "status": (f.get("status", {}) or {}).get("name", ""),
                "severity": _reverse_priority(
                    (f.get("priority", {}) or {}).get("name", "Medium")
                ),
            })
        return issues


def _build_description(description: str, reproduce_steps: str) -> str:
    parts = [description]
    if reproduce_steps:
        parts.append(f"\n复现步骤:\n{reproduce_steps}")
    return "\n".join(parts)


def _reverse_priority(name: str) -> int:
    mapping = {"Highest": 1, "High": 2, "Medium": 3, "Low": 4}
    return mapping.get(name, 3)


TRACKER_REGISTRY["jira"] = JiraBugManager
