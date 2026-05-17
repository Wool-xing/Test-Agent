"""Typer CLI: `tagent run|status|report|catalog|doctor`."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

import runtime
from runtime.api.deps import Kernel
from runtime.api.parsers import parse_path, parse_text, parse_url
from runtime.cli.config import config_app
from runtime.config.settings import get_settings

# Fix Unicode and SSL on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    # Suppress SSL verification errors from corporate proxies / missing certs
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_SMOKE_PRD_FIXTURE = """\
# Smoke PRD · 登录模块(fixture)

> Test-Agent 自检 fixture · 主宪章 §33。
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

app = typer.Typer(add_completion=False, help="Test-Agent Runtime CLI")
app.add_typer(config_app, name="config")
console = Console(force_terminal=True)


@app.callback(invoke_without_command=True)
def _version_callback(
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
):
    if version:
        console.print(f"Test-Agent Runtime v{runtime.__version__}")
        raise typer.Exit(0)
_kernel = Kernel()


@app.command()
def run(
    target: str = typer.Argument(..., help="path / url / free-form text"),
    note: str = typer.Option("", "--note", help="extra hint to the router"),
    no_persist: bool = typer.Option(False, "--no-persist", help="skip DB write"),
    json_only: bool = typer.Option(False, "--json", help="print full result JSON only"),
    mode: str = typer.Option("exec", "--mode", help="exec | learn | silent (charter §23)"),
    lang: str = typer.Option("zh", "--lang", help="zh | en | zh-en"),
):
    """Plan + execute a test run."""
    from runtime.tutor.i18n import set_lang
    from runtime.tutor.verbosity import set_mode

    set_mode(mode)
    set_lang(lang)
    art = _build_artifact(target, note)
    run_id, decision = _kernel.submit(art, persist=not no_persist)
    if not json_only:
        console.print(f"[bold green]run_id[/]: {run_id}")
        console.print(f"target_type: {decision.detected_target_type}  confidence={decision.confidence:.2f}")
        console.print("rationale:", decision.rationale)
        _print_dag(decision)
    summary = _kernel.execute_sync(run_id, decision)
    if json_only:
        typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        console.print(
            f"[bold]done[/]: {summary['succeeded']}/{summary['total']} ok, {summary['failed']} failed"
        )


@app.command()
def catalog():
    """List experts + skills loaded from markdown."""
    data = _kernel.catalog()
    t = Table(title=f"Catalog: {data['counts']['experts']} experts + {data['counts']['skills']} skills")
    t.add_column("kind")
    t.add_column("name")
    t.add_column("description")
    for e in data["experts"]:
        t.add_row(e["kind"], e["name"], e["description"][:80])
    for s in data["skills"]:
        t.add_row(s["kind"], s["name"], s["description"][:80])
    console.print(t)


@app.command()
def plan(
    target: str = typer.Argument(...),
    note: str = typer.Option("", "--note"),
    out: Path | None = typer.Option(None, "--out", help="write decision JSON to file"),
):
    """Plan only (no execution)."""
    art = _build_artifact(target, note)
    decision = _kernel.decide(art)
    payload = decision.model_dump()
    if out:
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"decision written -> {out}")
    else:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command()
def doctor(
    agents: bool = typer.Option(False, "--agents", help="L1 frontmatter lint + optional --probe LLM ping"),
    probe: bool = typer.Option(False, "--probe", help="L3 real LLM ping each agent once (~$0.5, charter §33)"),
    llm_smoke: bool = typer.Option(False, "--llm-smoke", help="L3 5s round-trip smoke test (single real LLM call, verify first-mile + token/cost)"),
):
    """Sanity check: settings + catalog + optional DB/MinIO ping + L1/L3 self-check."""
    s = get_settings()
    console.print("[bold]Settings:[/]")
    console.print(f"  project_root      = {s.project_root}")
    console.print(f"  llm_provider      = {s.llm_provider} (fallback {s.llm_provider_fallback})")
    console.print(f"  db_url            = {s.db_url}")
    console.print(f"  minio_endpoint    = {s.minio_endpoint}")
    console.print(f"  otel_enabled      = {s.otel_enabled}")
    cat = _kernel.catalog()
    console.print(f"\n[bold]Catalog:[/] {cat['counts']['experts']} experts, {cat['counts']['skills']} skills")
    _ping_db()
    _ping_minio()

    if agents:
        from runtime.healthcheck.agent_smoke import run_smoke

        console.print("\n[bold]L1 frontmatter lint:[/]")
        report = run_smoke()
        if report.ok:
            console.print(f"[green]OK[/] agents={report.expert_count}/16 skills={report.skill_count}/32")
        else:
            console.print(f"[red]FAIL[/] {len(report.issues)} issue(s):")
            for i in report.issues:
                console.print(f"  - {i}")
            raise typer.Exit(1)

    if llm_smoke:
        from runtime.healthcheck.llm_smoke import run_llm_smoke

        console.print("\n[bold]L3 LLM smoke (single round-trip 'Hello'):[/]")
        r = run_llm_smoke()
        mark = "[green]✓[/]" if r.ok else "[red]✗[/]"
        console.print(f"  {mark} {r.provider} / {r.model}  {r.latency_ms} ms")
        if r.response:
            console.print(f"    response: {r.response!r}")
        if r.prompt_tokens or r.completion_tokens:
            console.print(f"    tokens:   prompt={r.prompt_tokens} completion={r.completion_tokens}")
        if r.cost_usd > 0:
            console.print(f"    cost:     ${r.cost_usd:.6f}")
        if r.reason:
            console.print(f"    reason:   {r.reason}")
        if not r.ok:
            raise typer.Exit(1)

    if probe:
        from runtime.healthcheck.llm_probe import probe_all_agents

        console.print("\n[bold]L3 LLM probe (real call, charter §33):[/]")
        results = probe_all_agents()
        for r in results:
            mark = "[green]✓[/]" if r.ok else "[red]✗[/]"
            console.print(f"  {mark} {r.name:30}  {r.latency_ms:>5} ms  {r.reason or ''}")
        failed = [r for r in results if not r.ok]
        if failed:
            console.print(f"[red]{len(failed)}/{len(results)} agents probe failed[/]")
            raise typer.Exit(1)
        console.print(f"[green]all {len(results)} agents responded[/]")


@app.command()
def selftest(
    e2e: bool = typer.Option(False, "--e2e", help="L3 full E2E (read fixture PRD -> 16 agent DAG -> execute -> persist, real LLM, ~$3)"),
    fixture: str = typer.Option("examples/_smoke_prd.md", "--fixture", help="PRD fixture path"),
    persist: bool = typer.Option(False, "--persist", help="write to DB"),
    strict: bool = typer.Option(False, "--strict", help="100% node pass rate required; default >=80% (charter §33 tolerant)"),
    pass_threshold: float = typer.Option(0.80, "--pass-threshold", help="minimum pass rate 0.0-1.0 in non-strict mode"),
):
    """L3 full self-test (charter §33, required before tagging).

    Default tolerant mode: pass if node pass rate >= threshold (0.80).
    Fixture e2e tolerates partial failures (some nodes need runtime input).
    --strict disables tolerance: any node fail = overall fail (pre-release check).
    """
    if not e2e:
        console.print("[yellow]nothing to do; pass --e2e[/]")
        raise typer.Exit(0)

    fixture_path = Path(fixture)
    if not fixture_path.exists():
        console.print(f"[red]fixture not found:[/] {fixture}")
        raise typer.Exit(2)

    console.print(f"[bold]L3 E2E selftest[/]  fixture={fixture}  mode={'strict' if strict else f'tolerant ≥{pass_threshold:.0%}'}")
    art = parse_path(fixture_path)
    run_id, decision = _kernel.submit(art, persist=persist)
    console.print(f"  run_id      = {run_id}")
    console.print(f"  target_type = {decision.detected_target_type}  confidence={decision.confidence:.2f}")
    console.print(f"  dag nodes   = {len(decision.dag)}")
    summary = _kernel.execute_sync(run_id, decision)

    total = summary["total"]
    succ = summary["succeeded"]
    # L2-C: tolerant 模式排除 V1.x rollout 节点 (env-manager 等未实装的) 不拉低通过率;
    # strict 模式仍严格 (所有节点必过, 含 rollout)
    rollout_skipped = summary.get("rollout_skipped", [])
    n_skipped = len(rollout_skipped)
    if strict:
        ok = summary["failed"] == 0
        rate = succ / total if total else 0.0
        label = "strict (100%, 含 rollout)"
    else:
        # 把 rollout 节点从分母排除 (它们是 V1.x 计划内未实装, 非真 fail)
        effective_total = max(1, total - n_skipped)
        # rollout 节点也从 failures 数移除 (effective succ 不变, 但分母减)
        rate = succ / effective_total
        ok = rate >= pass_threshold
        label = f"tolerant ≥{pass_threshold:.0%} (排除 {n_skipped} 个 rollout)"

    mark = "[green]✓ PASS[/]" if ok else "[red]✗ FAIL[/]"
    skip_hint = f" / {n_skipped} rollout" if n_skipped else ""
    console.print(
        f"{mark}  {succ}/{total} ok ({rate:.0%}, {label})  "
        f"{summary['failed']} failed{skip_hint}"
    )
    if not ok:
        raise typer.Exit(1)


def _build_artifact(target: str, note: str):
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


def _print_dag(decision):
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

    # Charter §23 教学层渲染
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


def _ping_db():
    try:
        from sqlalchemy import text

        from runtime.storage.db import get_engine

        with get_engine().connect() as c:
            c.execute(text("SELECT 1"))
        console.print("[green]DB    OK[/]")
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]DB    skip ({e})[/]")


def _ping_minio():
    try:
        from runtime.storage.objects import ObjectStore

        ObjectStore()._conn()  # noqa: SLF001
        console.print("[green]MinIO OK[/]")
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]MinIO skip ({e})[/]")


@app.command()
def search(
    keyword: str = typer.Argument(...),
    lane: str = typer.Option(None, "--lane", help="skills | agents | mcp | hooks"),
):
    """Search marketplace registry."""
    from runtime.marketplace.catalog import search as catalog_search

    results = catalog_search(keyword, lane=lane)
    if not results:
        console.print("[yellow]no match[/]")
        return
    t = Table(title=f"Marketplace search: {keyword}")
    for col in ("name", "lane", "version", "source_tier", "confidence", "score"):
        t.add_column(col)
    for e in results:
        t.add_row(e.name, e.lane, e.version, e.source_tier, e.confidence, str(e.safety_score))
    console.print(t)


@app.command(name="list")
def list_cmd(lane: str = typer.Option(None, "--lane")):
    """List installed marketplace entries."""
    from runtime.marketplace.catalog import load_local

    entries = load_local()
    if lane:
        entries = [e for e in entries if e.lane == lane]
    if not entries:
        console.print("[yellow]nothing installed[/]")
        return
    t = Table(title="Installed marketplace entries")
    for col in ("name", "lane", "version", "tier", "installed_at"):
        t.add_column(col)
    for e in entries:
        t.add_row(e.name, e.lane, e.version, e.source_tier, e.installed_at or "—")
    console.print(t)


@app.command()
def install(
    name: str = typer.Argument(...),
    lane: str = typer.Argument(...),
    source: str = typer.Option(..., "--source", help="path to skill .md / agent .md / mcp config / hook"),
    tier: str = typer.Option("low", "--tier"),
    version: str = typer.Option("1.32.0", "--version"),
):
    """Install marketplace entry through 4 safety gates."""
    import hashlib

    from runtime.marketplace.catalog import Entry
    from runtime.marketplace.installer import install as do_install

    p = Path(source)
    if not p.exists():
        console.print(f"[red]source not found:[/] {source}")
        raise typer.Exit(2)
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    entry = Entry(name=name, version=version, lane=lane, source_url=str(p.resolve()),
                   sha256=sha, license="MIT", source_tier=tier)
    res = do_install(entry, p)
    if res["ok"]:
        console.print(f"[green]installed[/] {name} → {res['path']}")
    else:
        console.print(f"[red]blocked[/] {res.get('blocked_by')}")
        for r in res.get("reasons", []):
            console.print(f"  - {r}")
        raise typer.Exit(1)


@app.command()
def uninstall(name: str = typer.Argument(...)):
    """Uninstall (archive only, irreversible per §22)."""
    from runtime.marketplace.installer import uninstall as do_uninstall

    res = do_uninstall(name)
    if res["ok"]:
        console.print(f"[yellow]archived[/] {name} → {res['archived_to']}")
    else:
        console.print(f"[red]failed[/] {res.get('error')}")
        raise typer.Exit(1)


@app.command()
def demo(
    out: str = typer.Option("workspace/_demo", "--out", help="demo output dir (.env / tagent.yml / STARTUP.md / test cases / reports)"),
    preset: str = typer.Option("minimal", "--preset", help="init preset · minimal=offline 0-config (stub LLM + webhook)"),
    keep: bool = typer.Option(False, "--keep", help="keep previous output (default overwrites each run)"),
    real_llm: bool = typer.Option(False, "--real-llm", help="real LLM path (reads TAGENT_LLM_PROVIDER + credentials), 16-agent DAG ~$1-3 / 60-120s · default stub"),
    skip_smoke: bool = typer.Option(False, "--skip-smoke", help="skip pre-flight smoke test before --real-llm"),
    yes: bool = typer.Option(False, "-y", "--yes", help="skip cost confirmation prompt for --real-llm"),
):
    """One-command full demo · default 0-config stub · --real-llm for real LLM (charter §1 §7)."""
    import os
    import shutil
    import sys

    # W4-5 实测 Windows 修: Python 默认 GBK 编码 → demo 输出 ✓ 等字符炸
    # UnicodeEncodeError。Windows 平台兜底设 UTF-8 (用户未设时), 不覆盖用户显式设置。
    if sys.platform == "win32":
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")
        os.environ.setdefault("PYTHONUTF8", "1")

    if real_llm:
        # --real-llm: read real credentials from env; smoke-test first to avoid failing after 16-agent run
        provider = os.getenv("TAGENT_LLM_PROVIDER", "(unset -> using settings default)")
        console.print(f"[bold yellow]⚠ --real-llm mode[/]  provider={provider}")
        console.print("  · Real LLM calls ~$1-3 / 60-120s (16 agents × multi-turn)")
        console.print("  · Will raise during selftest if provider unset or credentials missing")
        if not yes:
            if not typer.confirm("  Continue? (N=exit)", default=False):
                raise typer.Exit(0)

        if not skip_smoke:
            from runtime.healthcheck.llm_smoke import run_llm_smoke

            console.print("\n[bold]Pre-flight · doctor --llm-smoke (single round-trip)[/]")
            r = run_llm_smoke()
            mark = "[green]✓[/]" if r.ok else "[red]✗[/]"
            console.print(f"  {mark} {r.provider} / {r.model}  {r.latency_ms} ms  {r.reason or ''}")
            if not r.ok:
                console.print("  [red]LLM unreachable -> exiting (not wasting 16-agent run). Fix config or add --skip-smoke[/]")
                raise typer.Exit(1)
            if r.response:
                console.print(f"    response: {r.response!r}")
    else:
        # stub path: set env + clear settings cache before Kernel/Router instantiation (otherwise _kernel locked to claude)
        os.environ["TAGENT_LLM_PROVIDER"] = "stub"
        os.environ["TAGENT_LLM_PROVIDER_FALLBACK"] = "stub"

    import runtime.config.settings as _settings_mod

    _settings_mod._settings = None
    from runtime.api.deps import Kernel as _Kernel
    demo_kernel = _Kernel()

    from runtime.init.matrix import load_matrix
    from runtime.init.renderer import render_all
    from runtime.init.wizard import from_preset

    mode_label = "real LLM" if real_llm else "stub LLM"
    console.print(f"\n[bold cyan]Test-Agent · One-Command Demo[/]  (charter §1 §7, {mode_label})\n")

    out_path = Path(out)
    if out_path.exists() and not keep:
        console.print(f"[dim]Clearing previous output {out_path}[/]")
        shutil.rmtree(out_path, ignore_errors=True)
    out_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]Step 1/4 · tagent init --preset {preset}[/]")
    matrix = load_matrix()
    answers = from_preset(preset, matrix=matrix)
    res = render_all(answers, out_path, matrix=matrix, overwrite=True)
    console.print(f"  ✓ {res.env_path.name}  /  {res.yml_path.name}  /  {res.startup_path.name}")

    console.print("\n[bold]Step 2/4 · tagent doctor --agents (L1 frontmatter lint)[/]")
    from runtime.healthcheck.agent_smoke import run_smoke

    report = run_smoke()
    if report.ok:
        console.print(f"  ✓ agents={report.expert_count}/16  skills={report.skill_count}/32")
    else:
        console.print(f"  [red]✗ {len(report.issues)} issue(s)[/]")
        raise typer.Exit(1)

    step3_label = "real LLM · ~$1-3" if real_llm else "stub LLM · 0 cost"
    console.print(f"\n[bold]Step 3/4 · tagent selftest --e2e (16 agent DAG · {step3_label})[/]")
    fixture_path = Path("examples/_smoke_prd.md")
    if not fixture_path.exists():
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(_SMOKE_PRD_FIXTURE, encoding="utf-8")
        console.print(f"  [yellow]⚡ auto-generated fixture:[/] {fixture_path}")
    art = parse_path(fixture_path)
    run_id, decision = demo_kernel.submit(art, persist=False)
    summary = demo_kernel.execute_sync(run_id, decision)
    total = summary["total"]
    succ = summary["succeeded"]
    rate = succ / total if total else 0.0
    console.print(f"  ✓ DAG executed: {succ}/{total} ok ({rate:.0%})")

    console.print("\n[bold]Step 4/4 · Artifacts[/]")
    artifacts = []
    for d in (Path("workspace/测试用例"), Path("workspace/测试报告"), Path("workspace/执行日志")):
        if d.exists():
            for f in sorted(d.glob("**/*")):
                if f.is_file() and not f.name.startswith("_"):
                    artifacts.append(f)
    if artifacts:
        for f in artifacts[:12]:
            console.print(f"  · {f}")
        if len(artifacts) > 12:
            console.print(f"  · [dim]... +{len(artifacts) - 12} more[/]")
    else:
        console.print("  [yellow](no artifacts · script dependencies may be missing, run `pip install -r requirements.txt`)[/]")

    console.print(f"\n[bold green]✓ demo done[/]  config: {out_path}  artifacts: workspace/")
    console.print(f"[dim]Next: `cat {res.startup_path}` for startup guide; edit `.env` to use real LLM[/]")


@app.command()
def init(
    test_type: str = typer.Option("", "--test-type", help="web/api/mobile/desktop/iot/car/ai_model/security (non-interactive mode)"),
    platform: str = typer.Option("", "--platform", help="linux/windows/mac/android/ios/embedded"),
    llm: str = typer.Option("", "--llm", help="claude/openai/qwen/deepseek/ollama"),
    bug_tracker: str = typer.Option("", "--bug-tracker", help="zentao/jira/github/gitlab/linear/webhook (default zentao)"),
    notifier: str = typer.Option("", "--notifier", help="comma-separated: wechat,feishu,dingtalk,slack,email,teams"),
    preset: str = typer.Option("", "--preset", help="minimal/saas-web/mobile-android/security-pentest"),
    out: str = typer.Option("workspace", "--out", help="output dir (.env / tagent.yml / STARTUP.md)"),
    overwrite: bool = typer.Option(False, "--overwrite", help="allow overwriting existing .env/tagent.yml/STARTUP.md"),
):
    """Generate .env + tagent.yml + STARTUP.md in 5 minutes (charter §1 one-command deploy + §7)."""
    from runtime.init.matrix import load_matrix
    from runtime.init.renderer import render_all
    from runtime.init.wizard import InitAnswers, from_args, from_preset, run_wizard

    matrix = load_matrix()

    if preset:
        answers = from_preset(preset, matrix=matrix)
        console.print(f"[green]preset[/] {preset}: {answers.test_type}/{answers.platform}/{answers.llm_provider}/{answers.bug_tracker} + {answers.notifiers}")
    elif test_type and platform and llm:
        notifiers = [n.strip() for n in notifier.split(",") if n.strip()] or ["wechat"]
        answers = from_args(
            test_type=test_type,
            platform=platform,
            llm_provider=llm,
            bug_tracker=bug_tracker or "zentao",
            notifiers=notifiers,
            matrix=matrix,
        )
        console.print(f"[green]args[/] {answers.test_type}/{answers.platform}/{answers.llm_provider}/{answers.bug_tracker} + {answers.notifiers}")
    else:
        answers = run_wizard(matrix=matrix)

    try:
        res = render_all(answers, Path(out), matrix=matrix, overwrite=overwrite)
    except FileExistsError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(2)

    console.print("\n[bold green]✓ config generated[/]")
    console.print(f"  .env       → {res.env_path}")
    console.print(f"  tagent.yml → {res.yml_path}")
    console.print(f"  STARTUP.md → {res.startup_path}")
    console.print(f"\n[bold]Next[/]: `cat {res.startup_path}` for startup guide")


@app.command()
def export(
    plan: str = typer.Argument(..., help="TestCaseTree JSON path (testcase-designer output)"),
    format: str = typer.Option("xmind", "--format", help="xmind | markmap | opml | all"),
    out: str = typer.Option("", "--out", help="output file (single format only)"),
    out_dir: str = typer.Option("workspace/testcases", "--out-dir", help="output dir when --format all"),
):
    """Export TestCaseTree to xmind / markmap / opml / all (charter §5 multi-format I/O)."""
    from runtime.exporters import xmind as _x  # noqa: F401 ensure registration
    from runtime.exporters import markmap as _m  # noqa: F401
    from runtime.exporters import opml as _o  # noqa: F401
    from runtime.exporters.base import REGISTRY, TestCaseNode, TestCaseTree, get_exporter

    plan_path = Path(plan)
    if not plan_path.is_file():
        console.print(f"[red]plan not found:[/] {plan}")
        raise typer.Exit(2)
    raw = json.loads(plan_path.read_text(encoding="utf-8"))
    tree = _tree_from_dict(raw)

    formats = sorted(REGISTRY) if format == "all" else [format]
    written: list[Path] = []
    for fmt in formats:
        if fmt not in REGISTRY:
            console.print(f"[red]unknown format:[/] {fmt}; available={sorted(REGISTRY)}")
            raise typer.Exit(2)
        exp = get_exporter(fmt)
        if format == "all" or not out:
            target = Path(out_dir) / f"{tree.project_name}{exp.extension}"
        else:
            target = Path(out)
        target.parent.mkdir(parents=True, exist_ok=True)
        final = exp.export(tree, target)
        written.append(final)
        console.print(f"[green]{fmt}[/] → {final}")
    if format == "all":
        console.print(f"[bold]done[/]: {len(written)} files written under {out_dir}")


def _tree_from_dict(d: dict) -> "TestCaseTree":
    from runtime.exporters.base import TestCaseNode, TestCaseTree

    def _node(n: dict) -> TestCaseNode:
        return TestCaseNode(
            title=n.get("title", "(untitled)"),
            kind=n.get("kind", "feature"),
            priority=n.get("priority"),
            preconditions=list(n.get("preconditions", [])),
            expected=list(n.get("expected", [])),
            notes=n.get("notes", ""),
            tags=list(n.get("tags", [])),
            id=n.get("id", ""),
            children=[_node(c) for c in n.get("children", [])],
        )

    return TestCaseTree(
        project_name=d.get("project_name", "untitled"),
        root=_node(d.get("root", {"title": "root"})),
        version=d.get("version", "1.0"),
        author=d.get("author", "Test-Agent"),
    )


@app.command()
def verify(
    source: str = typer.Argument(...),
    skip_sandbox: bool = typer.Option(False, "--skip-sandbox"),
    skip_darwin: bool = typer.Option(False, "--skip-darwin"),
):
    """Run 4 safety gates without install."""
    from runtime.marketplace.verifier import run_all_gates

    p = Path(source)
    if not p.exists():
        console.print(f"[red]not found:[/] {source}")
        raise typer.Exit(2)
    results = run_all_gates(p, skip_sandbox=skip_sandbox, skip_darwin=skip_darwin)
    t = Table(title=f"Verify: {p.name}")
    for col in ("gate", "passed", "score", "reason"):
        t.add_column(col)
    for g in results:
        t.add_row(g.gate, "✓" if g.passed else "✗", str(g.score or "—"), g.reason or "—")
    console.print(t)


if __name__ == "__main__":
    app()
