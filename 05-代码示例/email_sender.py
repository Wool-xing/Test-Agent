# SPDX-License-Identifier: MIT
"""
SMTP 邮件发送（含附件）
被引用方：09-报告生成 / 报告分发场景
"""
import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


def send_email(
    to: List[str],
    subject: str,
    body_html: str,
    attachments: Optional[List[str]] = None,
    cc: Optional[List[str]] = None,
    smtp_host: Optional[str] = None,
    smtp_port: Optional[int] = None,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
    sender: Optional[str] = None,
    use_tls: bool = True,
) -> bool:
    """发送邮件，支持 HTML body + 多附件（docx/pdf/zip 等）"""
    smtp_host = smtp_host or os.getenv("SMTP_HOST")
    smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
    smtp_user = smtp_user or os.getenv("SMTP_USER")
    smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
    sender = sender or smtp_user

    if not all([smtp_host, smtp_user, smtp_password, sender]):
        raise RuntimeError("SMTP 凭证未配置（SMTP_HOST/SMTP_USER/SMTP_PASSWORD）")

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    for path in attachments or []:
        p = Path(path)
        if not p.exists():
            logger.warning(f"附件不存在: {path}")
            continue
        with open(p, "rb") as f:
            part = MIMEApplication(f.read(), Name=p.name)
            part["Content-Disposition"] = f'attachment; filename="{p.name}"'
            msg.attach(part)

    recipients = list(to) + list(cc or [])
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            if use_tls:
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(sender, recipients, msg.as_string())
        logger.info(f"邮件已发送: {subject} → {to}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败: {e}")
        return False


def send_test_report_email(summary: dict, attachments: List[str],
                            to: List[str], cc: Optional[List[str]] = None) -> bool:
    """发送测试报告邮件（HTML 模板）"""
    pass_rate = summary.get("pass_rate", 0)
    verdict = summary.get("verdict", "通过")
    color = "#28a745" if verdict == "通过" else "#dc3545"

    body = f"""
<html><body style="font-family: -apple-system, sans-serif; max-width: 600px;">
<h2 style="color: {color};">{verdict} - {summary.get("project", "")}</h2>
<table border="1" cellpadding="6" style="border-collapse: collapse; width: 100%;">
  <tr><th>环境</th><td>{summary.get("environment", "")}</td></tr>
  <tr><th>用例数</th><td>{summary.get("total", 0)}</td></tr>
  <tr><th>通过率</th><td>{pass_rate:.1%}</td></tr>
  <tr><th>P0 Bug</th><td>{summary.get("p0_bugs", 0)}</td></tr>
  <tr><th>覆盖率</th><td>{summary.get("coverage", 0):.1%}</td></tr>
  <tr><th>性能 TPS</th><td>{summary.get("perf_tps", "-")}</td></tr>
  <tr><th>性能 P95</th><td>{summary.get("perf_p95", "-")} ms</td></tr>
</table>
<p>详细报告见附件 / <a href="{summary.get("report_url", "#")}">在线版</a></p>
</body></html>
""".strip()

    return send_email(
        to=to, cc=cc,
        subject=f"[{verdict}] 测试报告 - {summary.get('project', '')}",
        body_html=body,
        attachments=attachments,
    )


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="SMTP 邮件发送")
    parser.add_argument("--to", required=True, nargs="+")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--attach", nargs="*", default=[])
    args = parser.parse_args()
    ok = send_email(to=args.to, subject=args.subject, body_html=args.body, attachments=args.attach)
    print("✅ 已发送" if ok else "❌ 失败")
