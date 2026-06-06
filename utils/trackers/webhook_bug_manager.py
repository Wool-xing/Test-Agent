# SPDX-License-Identifier: MIT
"""Webhook Bug 管理客户端 — BugTrackerBase 适配器。

通用 webhook 推送：POST JSON 到配置的 URL。
适用场景：企业微信/飞书/钉钉机器人、自建系统回调、Slack incoming webhook。

环境变量:
  WEBHOOK_BUG_URL — webhook 接收端点
  WEBHOOK_AUTH_HEADER — 可选认证头 (如 "Bearer xxx" 或 "Key yyy")
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from bug_tracker_base import BugTrackerBase, TRACKER_REGISTRY
except ImportError:
    from utils.trackers.bug_tracker_base import BugTrackerBase, TRACKER_REGISTRY

load_dotenv()
logger = logging.getLogger(__name__)


class WebhookBugManager(BugTrackerBase):
    def __init__(
        self,
        url: str | None = None,
        auth_header: str | None = None,
    ):
        self.url = url or os.getenv("WEBHOOK_BUG_URL", "")
        self.auth_header = auth_header or os.getenv("WEBHOOK_AUTH_HEADER", "")
        if not self.url:
            raise ValueError("WEBHOOK_BUG_URL 未配置")

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.auth_header:
            # Parse "Key: Value" or pass through as-is
            if ": " in self.auth_header:
                key, val = self.auth_header.split(": ", 1)
                headers[key] = val
            else:
                headers["Authorization"] = self.auth_header
        resp = requests.post(self.url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        if resp.text:
            try:
                return resp.json()
            except json.JSONDecodeError:
                return {"raw": resp.text}
        return {}

    def submit_bug(
        self,
        title: str,
        description: str,
        severity: int,
        attachments: list[str] | None = None,
        reproduce_steps: str = "",
    ) -> str:
        bug_id = str(uuid.uuid4())[:12]
        payload: dict[str, Any] = {
            "event": "bug.submit",
            "bug_id": bug_id,
            "title": title,
            "description": description,
            "severity": severity,
            "reproduce_steps": reproduce_steps,
        }
        if attachments:
            payload["attachments"] = attachments
        self._post(payload)
        logger.info("Webhook Bug 已推送: %s — %s", bug_id, title)
        return bug_id

    def get_status(self, bug_id: str) -> dict[str, Any]:
        logger.warning(
            "Webhook 适配器为单向推送，get_status 返回占位。BugID: %s", bug_id
        )
        return {
            "status": "unknown",
            "assignee": "",
            "severity": 3,
            "last_updated": "",
        }

    def add_comment(
        self, bug_id: str, comment: str, attachments: list[str] | None = None
    ) -> None:
        self._post({
            "event": "bug.comment",
            "bug_id": bug_id,
            "comment": comment,
        })
        logger.info("Webhook Bug %s: 已推送评论", bug_id)

    def link_testcase(self, bug_id: str, testcase_id: str) -> None:
        self._post({
            "event": "bug.link_testcase",
            "bug_id": bug_id,
            "testcase_id": testcase_id,
        })

    def query_open_bugs(
        self, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        logger.warning("Webhook 适配器为单向推送，query_open_bugs 返回空列表")
        return []


TRACKER_REGISTRY["webhook"] = WebhookBugManager
