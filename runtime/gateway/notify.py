"""Notification system — Slack, Email, Webhook (Sprint 6)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NotifyConfig:
    slack_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "test-agent@localhost"
    email_to: str = ""


@dataclass
class NotifyResult:
    ok: bool
    channel: str
    message: str = ""
    error: str | None = None


class Notifier:
    """Send test result notifications via Slack, Email, or Webhook."""

    def __init__(self, config: NotifyConfig | None = None):
        self._config = config or NotifyConfig()

    def send_slack(self, message: str) -> NotifyResult:
        """Send a message to Slack via webhook."""
        url = self._config.slack_webhook_url
        if not url:
            return NotifyResult(ok=False, channel="slack", error="Slack webhook URL not configured")
        try:
            import urllib.request
            import json
            data = json.dumps({"text": message}).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            return NotifyResult(ok=True, channel="slack", message=message[:100])
        except Exception as exc:
            return NotifyResult(ok=False, channel="slack", error=str(exc))

    def send_email(self, subject: str, body: str) -> NotifyResult:
        """Send an email notification."""
        if not self._config.smtp_host:
            return NotifyResult(ok=False, channel="email", error="SMTP host not configured")
        try:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = f"[Test-Agent] {subject}"
            msg["From"] = self._config.email_from
            msg["To"] = self._config.email_to

            with smtplib.SMTP(self._config.smtp_host, self._config.smtp_port, timeout=10) as smtp:
                if self._config.smtp_user:
                    smtp.starttls()
                    smtp.login(self._config.smtp_user, self._config.smtp_password)
                smtp.send_message(msg)
            return NotifyResult(ok=True, channel="email", message=f"Sent: {subject}")
        except Exception as exc:
            return NotifyResult(ok=False, channel="email", error=str(exc))

    def send_webhook(self, url: str, payload: dict) -> NotifyResult:
        """Send a generic webhook notification."""
        try:
            import urllib.request
            import json
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            return NotifyResult(ok=True, channel="webhook", message=str(url)[:80])
        except Exception as exc:
            return NotifyResult(ok=False, channel="webhook", error=str(exc))
