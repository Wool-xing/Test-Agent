# SPDX-License-Identifier: MIT
"""Linear Bug 管理客户端 — BugTrackerBase 适配器。

Linear GraphQL API (https://api.linear.app/graphql).
环境变量:
  LINEAR_API_KEY — Linear Personal API Key
  LINEAR_TEAM_ID — 默认团队 ID (如 TEAM-abc123)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv

from bug_tracker_base import BugTrackerBase, TRACKER_REGISTRY

load_dotenv()
logger = logging.getLogger(__name__)

SEVERITY_PRIORITY: dict[int, int] = {
    1: 1,  # Urgent
    2: 2,  # High
    3: 3,  # Medium
    4: 4,  # Low
}


class LinearBugManager(BugTrackerBase):
    def __init__(
        self,
        api_key: str | None = None,
        team_id: str | None = None,
    ):
        self.api_key = api_key or os.getenv("LINEAR_API_KEY", "")
        self.team_id = team_id or os.getenv("LINEAR_TEAM_ID", "")
        if not self.api_key:
            raise ValueError("LINEAR_API_KEY 未配置")

    def _gql(self, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = requests.post(
            "https://api.linear.app/graphql",
            json={"query": query, "variables": variables or {}},
            headers={"Authorization": self.api_key, "Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        if "errors" in body:
            raise RuntimeError(f"Linear GraphQL 错误: {body['errors']}")
        return body.get("data", {})

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
            body += f"\n\n复现步骤:\n{reproduce_steps}"
        priority = SEVERITY_PRIORITY.get(severity, 3)

        mutation = """
        mutation IssueCreate($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue { id identifier title }
          }
        }
        """
        variables: dict[str, Any] = {
            "input": {
                "title": title,
                "description": body,
                "priority": priority,
                "teamId": self.team_id,
            }
        }
        data = self._gql(mutation, variables)
        issue_create = data.get("issueCreate", {})
        identifier = (
            issue_create.get("issue", {}).get("identifier", "")
            if issue_create.get("success")
            else ""
        )
        logger.info("Linear Issue 已创建: %s — %s", identifier, title)
        return identifier

    def get_status(self, bug_id: str) -> dict[str, Any]:
        query = """
        query($id: String!) {
          issue(id: $id) {
            state { name }
            assignee { name }
            priority
            updatedAt
          }
        }
        """
        data = self._gql(query, {"id": bug_id})
        issue = data.get("issue", {}) or {}
        state = issue.get("state", {}) or {}
        return {
            "status": state.get("name", "unknown"),
            "assignee": (issue.get("assignee", {}) or {}).get("name", ""),
            "severity": issue.get("priority", 3),
            "last_updated": issue.get("updatedAt", ""),
        }

    def add_comment(
        self, bug_id: str, comment: str, attachments: list[str] | None = None
    ) -> None:
        mutation = """
        mutation($input: CommentCreateInput!) {
          commentCreate(input: $input) { success }
        }
        """
        self._gql(mutation, {"input": {"issueId": bug_id, "body": comment}})
        logger.info("Linear Issue %s: 已添加评论", bug_id)

    def link_testcase(self, bug_id: str, testcase_id: str) -> None:
        self.add_comment(bug_id, f"关联测试用例: `{testcase_id}`")

    def query_open_bugs(
        self, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        filter_clause = 'state { name { neq: "Done" } }'
        if filters:
            if "assignee" in filters:
                filter_clause += (
                    f', assignee {{ name {{ eq: "{filters["assignee"]}" }} }}'
                )
        query = """
        query($filter: IssueFilter!) {
          issues(filter: $filter, first: 100) {
            nodes {
              id identifier title
              state { name }
              priority
              assignee { name }
            }
          }
        }
        """
        data = self._gql(query, {
            "filter": {
                "team": {"id": {"eq": self.team_id}} if self.team_id else None,
            }
        })
        issues: list[dict[str, Any]] = []
        nodes = data.get("issues", {}).get("nodes", [])
        for node in nodes:
            issues.append({
                "bug_id": node.get("identifier", node.get("id", "")),
                "title": node.get("title", ""),
                "status": (node.get("state", {}) or {}).get("name", ""),
                "severity": node.get("priority", 3),
            })
        return issues


TRACKER_REGISTRY["linear"] = LinearBugManager
