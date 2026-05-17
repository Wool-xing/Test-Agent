"""Shared state + helpers for CLI commands. Avoids circular imports between commands/ and main."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from runtime.api.deps import Kernel
from runtime.api.parsers import parse_path, parse_text, parse_url
from runtime.config.settings import get_settings

# Fix Unicode and SSL on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

console = Console(force_terminal=True)
_kernel = Kernel()

_SMOKE_PRD_FIXTURE = """\
# Smoke PRD · 登录模块(fixture)

> Test-Agent 自检 fixture.
> **此文件不代表任何真实项目**,纯为 e2e 流程验证。

## 1. 背景

一个虚构的 SaaS 后台需要登录入口,本 PRD 用于触发 16 agent 的完整 DAG。

## 2. 功能要求

### 2.1 账号密码登录

- 用户输入账号 + 密码,点登录
- 后端校验,正确则颁发 session,跳转首页
- 错误:提示 "账号或密码错误"

### 2.2 短信验证码登录

- 用户输入手机号,点"发送验证码"
- 60 秒倒计时,验证码 6 位数字,5 分钟过期
- 错误次数 5 次锁定 10 分钟

### 2.3 安全要求

- 密码字段加密传输(HTTPS)
- 登录失败连续 5 次锁定账号
- 登录成功后 session 24 小时过期

## 3. 非功能

- 接口 P99 延迟 < 300ms
- 支持 1000 QPS 峰值
- 移动端 + 桌面端兼容

## 4. 不在范围

- 注册流程
- 找回密码
- 第三方 OAuth

## 5. 测试目标

让 Test-Agent 跑完 16 agent DAG,产出:
- 测试用例 Excel + xmind / markmap / opml
- 自动化脚本骨架
- 测试报告
"""


def build_artifact(target: str, note: str):
    p = Path(target)
    if target.startswith(("http://", "https://")):
        art = parse_url(target)
    elif p.exists():
        art = parse_path(p)
    else:
        art = parse_text(target)
    if note:
        art.text = (art.text or "") + "\n\n# Note:\n" + note
    return art


def print_dag(decision):
    from runtime.tutor.explainer import explain_node
    from runtime.tutor.verbosity import Mode, get_mode

    t = Table(title="Routing DAG")
    t.add_column("id")
    t.add_column("kind")
    t.add_column("name")
    t.add_column("depends_on")
    for n in decision.dag:
        t.add_row(n.id, n.kind, n.name, ",".join(n.depends_on) or "-")
    console.print(t)

    if get_mode() is not Mode.SILENT:
        for i, n in enumerate(decision.dag):
            console.print(f"\n[bold]🎯 Step {i+1}/{len(decision.dag)}[/] {n.name}")
            exp = explain_node(
                target=n.name,
                one_liner_zh=getattr(n, "one_liner_zh", "") or "(router 未填 one_liner)",
                one_liner_en=getattr(n, "one_liner_en", ""),
                why=getattr(n, "why", ""),
                theory_refs=list(getattr(n, "theory_refs", []) or []),
                alternatives=list(getattr(n, "alternatives", []) or []),
            )
            rendered = exp.render()
            if rendered:
                console.print(rendered)


def ping_db():
    try:
        from sqlalchemy import text
        from runtime.storage.db import get_engine
        with get_engine().connect() as c:
            c.execute(text("SELECT 1"))
        console.print("[green]DB    OK[/]")
    except Exception:  # noqa: BLE001
        console.print("[yellow]DB    skip (unavailable)[/]")


def ping_minio():
    try:
        from runtime.storage.objects import ObjectStore
        ObjectStore()._conn()  # noqa: SLF001
        console.print("[green]MinIO OK[/]")
    except Exception:  # noqa: BLE001
        console.print("[yellow]MinIO skip (unavailable)[/]")
