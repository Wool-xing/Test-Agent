# Test-Agent 完善计划（全球测试专家视角，2026）

> 基于 4 维度并行代理深度分析 + 行业标杆对标
> 分析来源: 架构审查 / 企业就绪度 / 开发者体验 / 测试方法论

---

## 总览

| 阶段 | 主题 | 条目数 | 预计 commits | 状态 |
| ------ | ------ | -------- | ------------- | ------ |
| Phase 1 | 安全基线 | 6 | 6-8 | ✅ done |
| Phase 2 | 诚实化 + DX + 拆分 | 8 | 8-12 | ✅ done |
| Phase 3 | 引擎加固 | 5 | 5-7 | ✅ done |
| Phase 4 | 测试智能 | 5 | 5-8 | ⏳ next |
| Phase 5 | 企业就绪 | 5 | 5-7 | ✅ done |
| Phase 6 | 开发者体验 | 5 | 4-6 | ✅ done |
| Phase 7 | 方法论深化 | 5 | 4-6 | ✅ done |
| Phase 8 | 平台化 | 5 | 4-6 | ✅ done |

---

## Phase 1: 安全基线（对外交付前必修）`✅ done 2026-05-17`

### #1 命令注入修复 (CWE-78)
- **文件**: `runtime/backends/local.py` — `create_subprocess_shell` → `create_subprocess_exec(*shlex.split(cmd))`
- **文件**: `runtime/backends/ssh.py` — shell `cat` → SFTP read; `shlex.quote()` cwd/env
- **文件**: `runtime/backends/ssh.py` — `known_hosts=None` → `known_hosts=()`

### #2 API 认证 + 安全加固
- **文件**: `runtime/api/main.py` — bearer auth middleware (gated by `TAGENT_API_AUTH_TOKEN`)
- **文件**: `runtime/api/main.py` — CORS 限制 `["http://localhost:*", "http://127.0.0.1:*", "tauri://localhost"]`
- **文件**: `runtime/api/main.py` — 文件上传 `max_length=50_000_000` + 扩展名白名单
- **文件**: `runtime/api/main.py` — `_run_results` `threading.Lock()` 保护
- **文件**: `runtime/api/deps.py` — 日志级别 `debug→warning/error`
- **文件**: `runtime/api/parsers.py` — PDF/DOCX 失败返回明确错误占位符

### #3 默认凭据清空 + 绑定 127.0.0.1
- **文件**: `runtime/config/settings.py` — `db_url` / `minio_access_key` / `minio_secret_key` 默认 → `""`
- **文件**: `runtime/config/settings.py` — `api_host` `"0.0.0.0"` → `"127.0.0.1"`; 加 `api_auth_token`

### #4 CI / 供应链安全
- **文件**: `.github/workflows/ci.yml` — `action-shellcheck@master` → `@2.0.0`
- **文件**: `.pre-commit-config.yaml` — `default_stages: [pre-commit]`
- **文件**: `install.sh` — 加安全建议 (推荐 `git clone` over `curl|bash`)

### #5 `utils/` 安全杂项
- `chaos_helper.py` — psutil absent → `RuntimeError` (not silent fallthrough)
- `protocol_helper.py` — SOAP XML `xml.sax.saxutils.escape()`
- `miniprogram_runner.py` — WebSocket `close()` wrap `try/finally`
- `i18n_checker.py` — `except Exception` → specific exceptions
- `api_retry_util.py` — `except: pass` → `logger.debug()`

### #6 `.gitignore` + 仓库清洁
- 加 10+ patterns (workspace/, runtime/workspace/, docs/审查报告/, etc.)
- 4 tracked .docx 测试报告 `git rm --cached`

---

## Phase 2: 诚实化 + DX + CLI 拆分 `✅ done 2026-05-17`

### #7 Karpathy 诚实化
- **文件**: `README.md` + `README.zh-CN.md` — "8640 combinations" → "~12 common combinations tested in CI"; "95% aspirational" → "Coverage is broad but not exhaustive"
- **文件**: `00-项目导航.md` — 移除 9 处 "主宪章 §X" 引用
- **文件**: `ROADMAP.md` — 移除 3 处 "主宪章" 引用
- **文件**: `utils/generate_report.py` — `generate_test_report()` 143→30 行, 提取 6 helper
- **文件**: `utils/mobile_driver.py` — `run_monkey()` 107→55 行, 提取 2 helper
- **文件**: `runtime/router/llm_client.py` — `_stub_response()` 77 行 if/elif → dispatch table 8 条目
- **文件**: `utils/fuzzer.py` — `ALL_PAYLOADS` 提升到模块级

### #8 CLI 拆分 + 冒烟测试
- **CLI 拆分** (680→39 行 main.py):
  - `runtime/cli/_shared.py` — kernel, console, 公共 helper
  - `runtime/cli/commands/catalog.py` — catalog 命令
  - `runtime/cli/commands/run.py` — run + plan 命令
  - `runtime/cli/commands/doctor.py` — doctor 命令
  - `runtime/cli/commands/selftest.py` — selftest 命令
  - `runtime/cli/commands/market.py` — marketplace 命令
  - `runtime/cli/commands/demo.py` — demo 命令
  - `runtime/cli/commands/init.py` — init 命令
  - `runtime/cli/commands/export.py` — export 命令
- **20 冒烟测试**:
  - `test_cli_commands.py` (5 tests) — 所有命令注册, --version, --help
  - `test_api_auth.py` (6 tests) — auth middleware, CORS, health
  - `test_build_artifact.py` (4 tests) — URL, file, text, note
  - `test_catalog.py` (5 tests) — experts/skills 计数, 字段验证

---

## Phase 3: 引擎加固（执行可靠性）`✅ done 2026-05-17`

### #9 自愈引擎（Self-Healing）✅
- **新建**: `runtime/self_healing/retry.py` — `with_retry()` 指数退避 (3 次, 2^n 秒)
- **新建**: `runtime/self_healing/locator_store.py` — 多属性元素定位 + 回退链
- **修改**: `scripts.py:49` — `subprocess.run()` 外包 `with_retry()`
- **修改**: `direct.py:22` — `_run_node()` `execute_node` 外包 `with_retry()`

### #10 Direct Executor 零重试 ✅
- **修改**: `direct.py:78-112` — 阻塞路径 + done_now 路径异常时 resubmit `_run_node` 最多 2 次

### #11 on_failure="skip" 空实现 ✅
- **修改**: `tasks.py:38-43` — skip 节点设 `summary["skipped"]=True`
- **修改**: `flows.py` + `direct.py` — skipped 独立追踪, 不计入 failures

### #12 共享 fixture 阻塞并行 ✅
- **修改**: `config/conftest.py:106` — `test_data` session→function + `tmp_path`
- **修改**: `config/conftest.py:150` — `browser_context` session→function

### #13 DAG 执行进度 + 断路器 ✅
- **修改**: `flows.py` + `direct.py` — `MAX_FAILURES=3` 断路器 + 进度日志
- **修改**: `tasks.py:14` — `timeout_seconds=3600`

---

## Phase 4: 测试智能（分析 & 决策）`✅ done 2026-05-17`

### #14 可观测性仪表板（Observability Dashboard）✅
- **新建**: `runtime/observability/dashboard.py` — 3 行布局 (decision→diagnostic→action)
- **修改**: `runtime/api/main.py` — `/dashboard` 端点使用新 builder
- **新增字段**: `decision` (pass_rate, trend, MTTD/MTTR), `diagnostic` (expert heatmap, flaky candidates, env_health), `actions` (P0/P1 action items)
- **向后兼容**: 保留所有原有字段

### #15 发布就绪评分（Release Readiness Score）✅
- **新建**: `runtime/orchestrator/release_readiness.py` — 加权评分独立模块
- **新建**: `runtime/cli/commands/readiness.py` — `tagent readiness` CLI
- **权重**: smoke×0.4 + regression×0.3 + perf×0.2 + security×0.1 → GREEN(≥0.85)/YELLOW(≥0.6)/RED
- **不改**: `test_lead.py` — 独立使用，不破坏现有逻辑

### #16 Flaky 测试自动隔离 ✅
- **修改**: `utils/flaky_detector.py` — 加 3 方法
- `detect_trends()` — P-F-P / F-P-F 模式检测 + confidence scoring
- `generate_quarantine()` — 隔离清单 (pytest --deselect 兼容)
- `generate_pytest_markers()` — @pytest.mark.flaky 配置生成

### #17 测试影响分析（Test Impact Analysis）✅
- **新建**: `runtime/intelligence/impact_analyzer.py` — AST 依赖图 + git diff → 影响测试
- `ImportGraph` 类 — 双向导入图 (imports / imported_by)
- `analyze_impact()` — 入口: git diff → AST scan → impacted test list
- **不改**: `regression_scope.py` — 独立工具

### #18 需求可追溯性 ✅
- **新建**: `utils/traceability_matrix.py` — 双向追溯矩阵
- `TraceabilityMatrix` 类 — 需求↔用例↔缺陷 自动链接
- `to_markdown()` — markdown 表格导出
- 覆盖率统计 + 未覆盖需求 + 孤儿 bug 检测

---

## Phase 5: 企业就绪（F500 采用）`✅ done 2026-05-17`

### #19 RBAC 访问控制 ✅
- **新建**: `runtime/api/rbac.py` — 4 角色 (admin/lead/tester/viewer) + `require_role()` 装饰器
- 通过 `TAGENT_ADMIN_TOKENS` 等 env 配置角色令牌
- 默认关闭 `TAGENT_RBAC_ENABLED=0` — 向后兼容
- **不改**: 现有 auth middleware

### #20 审计追踪 ✅
- **新建**: `runtime/observability/audit.py` — JSONL 追加审计日志
- `log_event()` — 记录 who/when/what/outcome
- `query_events()` — 按 action/resource/actor 过滤查询
- **不改**: 现有代码 — opt-in 集成

### #21 多租户 ✅
- **新建**: `runtime/api/tenancy.py` — contextvars 租户传播
- `get_current_tenant()` / `tenant_namespace()` / `tenant_prefix()`
- 默认关闭 `TAGENT_TENANCY_ENABLED=0` — 向后兼容
- **不改**: 现有 DB schema 或查询

### #22 启动时配置校验 ✅
- `runtime/config/settings.py` — `validate_startup()` 方法
- 检查: LLM key, 关键目录存在, psycopg/DB mismatch
- `runtime/cli/commands/doctor.py` — doctor 输出 config validation 段

### #23 执行生命周期钩子 ✅
- **新建**: `runtime/orchestrator/hooks.py` — `HookRegistry` (before/after/on_error)
- `runtime/orchestrator/direct.py` — `_run_node()` 集成 hook 触发点
- 钩子失败不中断执行

---

## Phase 6: 开发者体验（降低门槛）`✅ done 2026-05-17`

### #24 安装步骤从 15→3 ✅
- **新建**: `runtime/cli/commands/bootstrap.py` — `tagent bootstrap` 一站式命令
- 检测: Python/Git/pip 版本
- 配置: 自动生成 .env 模板
- 验证: LLM key 检查 + Runtime import

### #25 Debug 模式 + 日志级别开关 ✅
- `runtime/observability/logging.py` — `configure_logging()` 读取 `TAGENT_LOG_LEVEL` 环境变量
- `runtime/config/settings.py` — 新增 `log_level` 字段
- `runtime/cli/main.py` — `--debug` flag 设置 `TAGENT_LOG_LEVEL=DEBUG`

### #26 错误消息可操作化 ✅
- `runtime/api/main.py:219` — "internal error — see logs" → 包含 run_id + 日志路径 + `--debug` 提示
- `runtime/backends/modal.py:60,66` — "not connected" → "call connect() first"

### #27 新手教程 ✅
- **新建**: `docs/tutorial/TUTORIAL.md` — 5 步交互式教程 (clone→bootstrap→demo→custom→report)

### #28 Shell 自动补全 + --no-color ✅
- `runtime/cli/main.py` — Typer `add_completion=True` 启用 `tagent --install-completion`
- `runtime/cli/main.py` — `--no-color` flag
- `runtime/cli/_shared.py` — `set_no_color()` 切换 Rich console 为无色模式

---

## Phase 7: 方法论深化（测试科学性）`✅ done 2026-05-17`

### #29 分支覆盖率门禁 ✅
- `runtime/pyproject.toml` — pytest `addopts = "--cov-branch"` 启用分支覆盖率

### #30 测试代码静态分析 ✅
- `runtime/pyproject.toml` — pylint + radon 配置 (CC rank=B, max-line=110)

### #31 可移植性测试 ✅
- `runtime/tests/test_portability.py` — 7 tests: installability / coexistence / replaceability (ISO 25010)
- `runtime/pyproject.toml` — `@pytest.mark.portability` marker

### #32 量化风险矩阵 ✅
- `runtime/intelligence/risk_matrix.py` — Bayesian 概率校准 + 缓解后再评估
- RiskItem (概率×影响=暴露) + RiskMatrix (summary/markdown export)

### #33 分类树方法（ISTQB 第10项）✅
- `utils/classification_tree.py` — TreeModel + pairwise 组合生成 + 约束支持

---

## Phase 8: 平台化（生态 & 扩展）`✅ done 2026-05-17`

### #34 插件发现机制 ✅
- `runtime/marketplace/discovery.py` — `importlib.metadata` entry_points 发现
- 支持第三方包注册 agents/skills/backends (group=`tagent`)

### #35 测试数据合成引擎 ✅
- `utils/data_synthesizer.py` — PII 自动检测 + 确定性地掩码
- `mask_pii()` — 邮件/手机/身份证/IP/信用卡 5 类检测
- `synthesize_from_json()` — 递归 walk + 掩码 + 写入
- `subset_json()` — 随机子集提取

### #36 APM/Observability 预集成仪表板 ✅
- `runtime/observability/apm_export.py` — Datadog + Grafana dashboard JSON 导出
- `export_datadog_dashboard()` — pass rate, MTTD/MTTR, expert health, flaky
- `export_grafana_dashboard()` — stat + table panels with thresholds

### #37 用户旅程影响映射 ✅
- `runtime/intelligence/journey_mapper.py` — 故障→业务路径映射
- `map_failures_to_journeys()` — 基于模式匹配 (Registration/Login/Payment/...)
- `journey_impact_report()` — journeys_impacted + most_impacted

### #38 多地域合成监控 ✅
- `.github/workflows/synthetic-monitor.yml` — 每 6 小时 4 地域 (us-east/west, eu-west, ap-southeast)
- `tagent demo -y` + `tagent selftest --e2e` 定时执行

---

## 执行顺序

```
Phase 1 (#1→#6) ✅  ← 安全基线不打，后续白搭
Phase 2 (#7→#8) ✅  ← 诚实化 + CLI 拆分 + 冒烟测试
Phase 3 (#9→#13) ✅ ← 引擎不牢，上层白搭
Phase 4 (#14→#18) ✅ ← 有了可靠执行，才谈智能分析
Phase 6 (#24→#28) ✅ ← 降低门槛 = 更多人用 = 更多反馈
Phase 5 (#19→#23) ✅ ← 企业客户需要的基本保障
Phase 7 (#29→#33) ✅ ← 测试方法论的科学严谨性
Phase 8 (#34→#38) ✅ ← 生态扩展
```

**🎉 38/38 项全部完成。** 155 tests pass. 9/9 DAG demo ok.
