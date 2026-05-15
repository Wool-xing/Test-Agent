# Changelog

本文件记录 Test-Agent 工作流项目的所有可见变更。

格式参考 [Keep a Changelog 1.1.0](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)。

> 项目代号：`test-agent-team`（全英文内部代号）
> 中文别名：`Test-Agent 工作流搭建`

---

## [Unreleased]

_后续累积变更入此节;切版本时移到下方版本节。_

> ⚠️ **V1.15.0-alpha 至 V1.23.0-alpha (2026-05-15 ~ 2026-05-16) 共 9 版条目待补**。
> 版本历史见 [ROADMAP.md](ROADMAP.md#进度跟踪) 进度跟踪表与 `git log`。

---

## [v1.14.0-alpha] - 2026-05-12

> **首次正式版本切节**(W7-2, 2026-05-14): V1.1.0-alpha 到 V1.14.0-alpha 共 13 个内部 alpha 累积归入本节。后续新变更入 [Unreleased]。

### Added(V1.14.0-alpha · 5 核心 expert 真 LLM 落地 + 录制脚本 · 2026-05-12)

> 起因:战略参谋诚实交底——V1.13 的 selftest 100% PASS 是"骨架通"不是"内涵通",16 expert 里 11 个仍是 no-op。用户授权 C 路线(5 核心 expert 真 LLM)+ B(录制脚本)。

- **`runtime/orchestrator/agents/` 新模块**:
  - `base.py`:`AgentRunner` ABC + `RunnerContext` + `RunnerResult` + `AGENT_RUNNERS` registry + `@register` + `get_runner`
  - 5 concrete runner:`requirements_analyst.py` / `automation_engineer.py` / `test_executor.py` / `bug_manager.py` / `test_lead.py`
  - 每 runner 4 方法:`system_prompt` / `user_prompt(ctx)` / `mock_output(ctx)` / `output_file(ctx)` + `summary()`
  - **stub provider 自动走 `mock_output`**(CI / selftest 0 成本 0 LLM 调用)
  - **真 LLM** 时:调 `aux_client.complete()` → 解析 JSON → 落盘 → 给下游
  - INDEX.md 文档化 5 runner schema + 上下游
- **adapter wiring**(`runtime/orchestrator/adapters/experts.py`):
  - `execute_node` 先查 `AGENT_RUNNERS`(优先 V1.14),fallback `SCRIPT_MAP`(主宪章 §9 不破坏)
  - `_upstream_outputs` 缓存:每 runner 产物给下游 RunnerContext.upstream
  - `reset_upstream_cache()` 由 flow 每 run 开头调
  - SCRIPT_MAP 路径排除 `artifact_text/lang/mode` 防多行文本炸 argparse
- **Kernel.submit 注入 `artifact_text`**(`runtime/api/deps.py`):每 DAG 节点 inputs 自动带原始 PRD 文本(20KB cap)
- **stub web-system DAG 加 test-lead**(`runtime/router/llm_client.py`):覆盖完整 9 节点 e2e 流程
- **5 真 runner 产物落盘**:
  - `workspace/执行日志/requirements_summary.json`(需求摘要 + P0/P1 + 风险区)
  - `workspace/执行日志/automation_scripts_plan.json`(脚本规划 + fixture 复用)
  - `workspace/执行日志/execution_plan.json`(4 阶段 + 失败 4 分类 + Flaky 规则)
  - `workspace/执行日志/bug_drafts.json`(BugTracker-ready Bug 草案 + severity 1-4)
  - `workspace/执行日志/decisions/final_verdict_*.json`(test-lead go/no-go 决策,标 `requires_human_signoff: true`)
- **录制脚本**(`scripts/`):
  - `_demo-commands.sh`:实际 demo 命令序列(被 record-demo-* 调)
  - `record-demo-asciinema.sh`:`asciinema rec` 自动录,产 .cast 可上传 asciinema.org 或转 GIF/SVG
  - `record-demo-obs.sh`:OBS / QuickTime 屏幕录制配套(用户摁录制 → 跑此脚本,节奏自动)
  - `docs/assets/terminalizer-config.yml`:精修 V1.14 配置(Catppuccin Mocha 主题 + UTF-8 + stub LLM env)
- **主宪章 §40 真 agent 落地 canon**:5 核心 + 11 fallback + 加新 runner 流程 + RunnerContext / RunnerResult 协议
- 烟测:**9/9 strict PASS · 5 真 runner 产物全落盘**(原 V1.13 8/8 是 3 script + 5 no-op,V1.14 是 5 真 runner + 3 script + 1 no-op)
- 版本 V1.13.0-alpha → **V1.14.0-alpha**

### Added(V1.13.0-alpha · README hero 重写 + `tagent demo` + 30 秒 demo 录制脚本 · 2026-05-12)

- **`tagent demo` 子命令**:0 API key / 0 配置一键跑通 4 步——init minimal preset + L1 lint + L2 e2e + 产物清单
  - 自动 stub LLM + 重置 settings 缓存,避免 `_kernel` 模块加载顺序问题
  - 产 36+ 文件:Excel 用例 + xmind/markmap/opml 思维导图 + Word 报告 + decision logs
- **README hero 重写**(双语):
  - 头 30 秒区:`tagent demo` 作首屏 hook(从 0 到产物 30 秒)
  - 次屏:`tagent init --preset` 5 选,带 STARTUP.md 引导
  - 强调 8640 种配置组合 + 6 BugTracker + 6 通知 + 4 层自检 + MCP 6 件套
- **30 秒 demo 录制脚本**(`docs/assets/demo-script-v1.12.md`):
  - 逐秒分镜表(0-3s logo / 3-6s init / 6-10s 产物 / 10-14s STARTUP / 14-18s doctor / 18-25s demo / 25-30s github CTA)
  - Terminalizer + asciinema + OBS 三种录制方案
  - 渠道适配:Twitter/X · 微信视频号 · 掘金/V2EX · Hacker News(同一份素材 4 平台)
- **00-导航 同步**:CLI 行加 `demo` 子命令
- 烟测 `tagent demo` 产 36+ 文件全过 · L1/L3 strict 不破
- 版本 V1.12.0-alpha → **V1.13.0-alpha**

### Added(V1.12.0-alpha · `tagent init` 配置自动组装 · 5 分钟从 0 到可跑 · 2026-05-12)

- **新模块 `runtime/init/`**:
  - `matrix.py`:`load_matrix()` 加载 `04-配置文件/templates/matrix.yaml`(单源真理)
  - `wizard.py`:`run_wizard()` 交互向导 · `from_args()` 非交互 · `from_preset()` 5 预设
  - `renderer.py`:`render_all()` 把 InitAnswers + matrix + 模板 → `.env` + `tagent.yml` + `STARTUP.md`
- **新模板库 `04-配置文件/templates/`**:
  - `matrix.yaml` 单源真理:**8 测试类型 × 6 平台 × 5 LLM × 6 BugTracker × 6 通知 = 8640 组合**
  - `base.env.tpl` · `base.tagent.yml.tpl` · `STARTUP.md.tpl`(`{{var}}` 占位)
- **CLI**:`tagent init [--test-type] [--platform] [--llm] [--bug-tracker] [--notifier] [--preset] [--out] [--overwrite]`
- **5 预设**(开箱即用):
  - `minimal`(web/linux/ollama/webhook/email · 离线最小)
  - `saas-web`(web/linux/claude/github/slack+email · 海外 SaaS)
  - `国内-web`(web/linux/qwen/zentao/wechat+feishu+dingtalk · 国内合规)
  - `mobile-android`(mobile/android/claude/jira/slack)
  - `security-pentest`(security/linux/claude/github/email)
- **支持选项**:
  - 测试类型:web/api/mobile/desktop/iot/car/ai_model/security
  - 平台:linux/windows/mac/android/ios/embedded
  - LLM:claude/openai/qwen/deepseek/ollama
  - BugTracker(主宪章 §37):zentao/jira/github/gitlab/linear/webhook
  - 通知(主宪章 §36):wechat/feishu/dingtalk/slack/email/teams(可多选)
- **加新选项**:改 `matrix.yaml` 一处,wizard/CLI 自动列出(无需改代码)
- **STARTUP.md 启动指南**:含填占位清单 + 装依赖 hint + 健康检查 + 烟雾跑通命令 + 推荐 skill 顺序 + 出错对照表
- 烟测:5 preset × 全过 + 8 测试类型组合全过
- L1 + L3 strict 不破:agents=16/16 skills=32/≥25 + selftest 8/8 100%
- 版本 V1.11.0-alpha → **V1.12.0-alpha**

### Fixed(V1.11.0-alpha · 同步铁律批改 + BugTracker/多端 canon + n7 修 · 2026-05-12)

- **同步铁律(§1)执行**:17 文件批改"三端通知"→"多端通知";"禅道 Bug 提交"项目级框架→"BugTracker(默认禅道,可换 Jira/GitHub/GitLab/Linear/Webhook)"
  - `00-项目导航.md` · `02-专家定义/{01,07,08,09}.md` · `02-专家定义/README.md` · `03-技能定义/{README,test-coordinator,zentao-bug-submission}.md` · `04-配置文件/mcp-server-impl.md` · `05-代码示例/{README.md,api_retry_util.py}` · `06-CICD集成/{INDEX,CICD集成说明}.md` · `01-快速开始/{交付物清单,使用手册,配置清单}.md` · `examples/web-demo/README.md` · `CONTRIBUTING.md` · `FULL_GUIDE.md` · 私有源
- **adapter 修 V1.10 n7 bug**:`runtime/orchestrator/adapters/experts.py` 加 `SCRIPT_DEFAULT_ARGS` + `_ensure_fixture()` 通用机制
  - 现 `tagent selftest --e2e --strict` **100% PASS 8/8**(原 88% 7/8)
  - generate_report.py 默认注入 `--data=workspace/执行日志/_selftest_summary.json`,fixture 自动生成
- **主宪章扩**:
  - §36 多端通知 canon(扩 §6,6 渠道权威清单 + env 字段 + 业务语言铁律)
  - §37 BugTracker canon(扩 §12,6 adapter 权威清单 + measurement env + 措辞规范)
  - §10 五铭文 + §6 MCP 接入:"三端通知" → "多端通知"
- VERSION:1.10.0-alpha → **1.11.0-alpha**

### Added(V1.10.0-alpha · 4 层自检 + 精髓库三重防线 + 字体粗细 · 2026-05-12)

- **4 层自检铁律(主宪章 §33)**:
  - L1 frontmatter lint(无 LLM):`runtime/healthcheck/agent_smoke.py` + pre-push hook
  - L2 CI mock e2e(stub LLM,0 成本):`selftest-mock` job 每 push 跑
  - L3 真 LLM(~$4/release):`tagent doctor --agents --probe` + `tagent selftest --e2e`
  - L4 周自检(~$16/月):`.github/workflows/selftest-weekly.yml` 周一 03:00 UTC
- **`runtime/healthcheck/` 新模块**:`agent_smoke.py`(L1)+ `llm_probe.py`(L3)+ INDEX
- **CLI 新增/扩展**:
  - `tagent doctor --agents [--probe]`:L1 + 可选 L3 LLM ping 16 agent
  - `tagent selftest --e2e [--strict] [--pass-threshold 0.80]`:整体 e2e
- **`LLMClient.complete()`**:plain text completion(原仅 `complete_json`),probe 用
- **精髓库三重防线(主宪章 §34)**:
  - `.gitignore` 加 `_精髓库/` + `**/_精髓库/`
  - pre-commit hook `forbid-essence-library`(diff --cached 含路径即 reject)
  - CI file-count job 双校验
- **字体粗细统一(主宪章 §35)**:`docs/STYLE.md`(标题 ≤3 级,`**bold**` 仅 3 场景,中英空格)
- **补缺顶级 INDEX**:`docs/INDEX.md` + `examples/INDEX.md` + `profiles/INDEX.md` + `scripts/INDEX.md`
- **pre-tag hook**:`scripts/git-pre-tag.sh` 卡 `git tag v1.x`(7 天内必须有 L3 log)
- **fixture**:`examples/_smoke_prd.md` 触发完整 16 agent DAG
- 主宪章扩 §33/§34/§35;VERSION 1.9.0-alpha → **1.10.0-alpha**
- 烟雾测试:L1 16/16+32/≥25 全过;L2 stub e2e 88% PASS(7/8 节点)

### Added(V1.9.0-alpha · 用例多格式导出 · 用户自选 · 2026-05-12)

- **`runtime/exporters/` 新模块**(对标主宪章 §5 多格式 I/O):
  - `base.py`:`TestCaseTree` + `TestCaseNode` IR + `Exporter` ABC + `REGISTRY` + `@register` 装饰器
  - `xmind.py`:XMind 8/ZEN/2020+ `.xmind`(ZIP:content.json + metadata.json + manifest.json,P0→priority-1 marker 自动转,无第三方 lib)
  - `markmap.py`:Markmap `.md`(frontmatter + nested headings/list,GitHub README 直渲,markmap.js / VSCode 插件兼容)
  - `opml.py`:OPML 2.0 `.opml`(标准 XML,MindManager / Workflowy / Word / OmniOutliner 通用)
  - `INDEX.md`:索引 + IR 结构 + CLI 用法
- **CLI 子命令 `tagent export`**:
  ```bash
  tagent export plan.json --format xmind   --out workspace/测试用例/login.xmind
  tagent export plan.json --format markmap --out workspace/测试用例/login.md
  tagent export plan.json --format opml    --out workspace/测试用例/login.opml
  tagent export plan.json --format all     --out-dir workspace/测试用例/
  ```
- **`/testcase-design` skill 扩**:description 加多格式声明;末尾加 V1.9 思维导图 / 大纲段(Excel 仍是默认)
- **保留**:Excel 4-Sheet(`utils/excel_generator.py`)不动,§27 简洁优先
- **扩展点 P2 留位**:freemind / plantuml / mermaid-mindmap(按需加)
- 烟雾测试:3 exporter × sample TestCaseTree 全过(content.json 解析正常 / OPML XML 解析正常 / Markmap frontmatter 完整)
- 版本 V1.8.0-alpha → V1.9.0-alpha

### Added(V1.8.0-alpha · build-your-own-x 教学扩 + Marketplace 4 lane · 2026-05-12)

- **精髓库扩**:`_精髓库/build-your-own-x.md`(codecrafters/build-your-own-x curated list 萃取);加 INDEX 条目
- **教学层 KB 扩 13 大类**(原 12 → 13,加 `13-build-your-own/`):
  - INDEX + 10 P0 测试相关卡(database/network-stack/web-server/git/search-engine/shell/regex-engine/programming-language/web-browser/bot)
  - 每卡含 `estimated_time_hours` + 测试映射 + 推荐路径
- **主 skill**:`03-技能定义/build-your-own-x-explorer.md`(引导式 deep-dive 推荐)
- **Marketplace 4 lane 系统**(对标 Claude Code 官方):
  - `marketplace/{skills,agents,mcp,hooks}/` 目录
  - `marketplace/INDEX.md` + `registry.json` + `_safety_policy.yaml`(4 关安全门 + 3 信任级源)
  - `runtime/marketplace/`:catalog.py + verifier.py + installer.py + INDEX
  - 4 关安全门:签名校验(SHA256/ed25519) + 注入扫(复用 §22 scheduler 模块) + 沙箱试跑(Docker network=none) + darwin 评分(≥75)
- **CLI 加 5 子命令**:`tagent search/list/install/uninstall/verify`
- **主宪章 §30**:Marketplace 安全栅栏(4 关铁律 + 3 信任级 + safe-by-default + 不复制官方源 + 卸载只归档 + 紧急 kill switch)
- **主宪章 §31**:教学层扩 13 大类(byox P0/P1/P2 分档 + 预算检查 + essence_only policy)
- TOC 同步;skill 数升级
- 版本 V1.7.0-alpha → V1.8.0-alpha

### Added(V1.7.0-alpha · Karpathy 4 原则 + ECC 测试加固 + Essence 自动汲取 · 2026-05-12)

- **精髓库扩 2 条目**:
  - `_精髓库/karpathy-skills.md`(125k★ · LLM 写代码 4 原则元层)
  - `_精髓库/everything-claude-code.md`(179k★ · AI agent harness 性能优化 200 skill / 53 agent / Homunculus instincts / Selective install)
- **Karpathy 4 原则**(主宪章 §27,元层贯穿):Think Before / Simplicity First / Surgical Changes / Goal-Driven Execution;`03-技能定义/karpathy-guidelines/SKILL.md` 部署 upstream 原文(类 darwin-skill 不改本地)
- **ECC 6 测试 skill 入库**(对测试有用的,§28):
  - `tdd-workflow` · TDD 80%+ 覆盖
  - `verification-loop` · 5-phase verify(build→typecheck→lint→test→coverage)
  - `e2e-testing` · Playwright + 2FA/TOTP/SSO + 视觉回归 + 录屏
  - `eval-harness` · pass@k / Jaccard@k / top-1 / latency Δ
  - `security-review` · 代码层白盒 5 维(与 §25 pentest 应用层互补)
  - `agent-introspection-debugging` · 决策回放 + OTel + token + 上下文
- **Essence 自动汲取**(主宪章 §29):`runtime/essence_watcher/`
  - parser + tracker(gh API)+ delta_extractor(aux LLM)+ runner
  - 周期跑;新 commit → LLM 萃取 delta → 写 `_精髓库/{name}.update_{date}.md` 标 `llm-draft-unreviewed` 待审
  - `_精髓库_apply_policy.example.yaml`:auto_propose / essence_only / never 三档
  - safe-by-default:`tagent.yml essence_watcher.enabled: true` 才跑
- **主宪章新增 3 节**:§27 Karpathy 4 原则 / §28 ECC 测试加固 / §29 Essence 自动汲取 + TOC 同步
- 数字:14 skill → **32**(原 14 + 7 pentest + 5 automotive + 6 ECC) + `karpathy-guidelines/SKILL.md` upstream 1 个
- 版本 V1.6.0-alpha → V1.7.0-alpha

### Added(V1.6.0-alpha · 渗透&安全 + 车载&自动驾驶 双垂直专家+skill 集 · 2026-05-12)

- **精髓库扩**:`_精髓库/pentest-ai-agents.md` 合并萃取 pentagi(黑盒)+ shannon(白盒);10 节;含对比表+应用 checklist
- **2 新专家**:
  - `02-专家定义/15-渗透测试.md` `pentest-tester`(白盒+黑盒+5 攻击域 + Static-Dynamic Correlation + PoC-only)
  - `02-专家定义/16-车载测试.md` `automotive-tester`(ISO 26262 + AUTOSAR + HIL/SIL/MIL/PIL + ADAS + OTA + V2X)
- **7 新 pentest skill**:
  - `pentest-coordinator`(主)/ `pentest-recon` / `pentest-vuln` / `pentest-exploit` / `pentest-web` / `pentest-api` / `pentest-report`
- **5 新 automotive skill**:
  - `automotive-test`(主)/ `automotive-can-bus-test` / `automotive-adas-scenario` / `automotive-ota-update-test` / `automotive-hil-loop-test`
- **主宪章 §25**:渗透 & 安全测试强化(规则化:授权前置 / scope 防护 / prod 禁 / 沙箱 / PoC-only / 不可逆禁止 / 责任披露 / PII scrub)
- **主宪章 §26**:车载 & 自动驾驶强化(规则化:ASIL C/D 必 HIL / L4 极深 / OTA 必回退 / 公开道路授权 / 录波 MDF4 / PII 禁存 / 领域档案签字)
- **主宪章 §2 升级**:专家 14 → 16(核心 9 + 平台扩展 7)
- **TOC 同步**:加 §25 §26
- 数字:14 expert → **16** | 14 skill → **26**(7 pentest + 5 automotive 新增)
- 版本 V1.5.0-alpha → V1.6.0-alpha

### Added(V1.5.0-alpha · GBrain-inspired 强化 + 跨项目精髓库扩 · 2026-05-12)

- **精髓库扩**:`D:/项目文件/_精髓库/gbrain.md`(完整 10 节萃取,300+ 行)+ INDEX 更新
- **KB 自连图谱**:`runtime/tutor/graph.py`,零 LLM 抽取 typed link(6 种边:related_to/superseded_by/extends/prerequisite_of/contradicts/tool_implements);BFS walk + backlink-boosted ranking。实测 12 卡 → 40 edges + 44 nodes
- **eval 回放**:`runtime/tutor/eval_replay.py`,`TAGENT_EVAL_CAPTURE=1` opt-in;PII 自动 scrub(email/phone/SSN/API-key/card 6 类正则);replay 3 数(Jaccard@k/top-1 stability/latency Δ);默认 off
- **safe-by-default yaml 栅栏**:`runtime/config/safety.py` + `tagent.yml.example`;scheduler/curator/backends/gateway/destructive_ops 默认 deny;`assert_allowed` / `gate_*` 工厂函数;缺配置 → `SafeByDefaultBlocked` 异常
- **主宪章 §24**:GBrain-inspired 强化(自连图谱 + 混合检索 + eval 回放 + safe-by-default + PII 单源)+ TOC 同步
- 版本 V1.4.0-alpha → V1.5.0-alpha

### Added(V1.4.0-alpha · 教学层 · 用户边用边学 · 2026-05-12)

- **主宪章 §23 教学层准则**:exec(老手)/learn(新手)双模式 + 反幻觉 3 层 + 双语切换 + 持续累积
- **Theory KB**:`docs/theory/`,12 大类目录(工具/编程/基础理论/策略/方法/协议/平台/门禁/安全/AI测试/合规/流程)
  - `_schema.yaml`:卡片字段定义(id/category/level/authority/confidence/last_reviewed)
  - `_authority_sources.yaml`:权威源白名单(国际 ISTQB/IEEE/ISO/IEC/NIST/OWASP/MITRE/Google/Microsoft/Fowler/arXiv/ICSE/ISSTA + 中国 GB/T/等保/阿里/腾讯/美团/字节/CCF + AI HF/Anthropic/OpenAI/DeepEval + 经典书 Beizer/Myers/Crispin/Kaner)
  - 种子 12 张(每类 1 张):pytest / pytest-fixture / test-pyramid-2024 / shift-left / equivalence-partitioning / http-https / desktop-testing-windows / flaky-vs-reruns / owasp-top-10 / hallucination-evaluation / iec-62304 / bug-lifecycle;7 张完整中文 + 1 张完整双语
- **`runtime/tutor/` 教学层模块**:
  - `theory_kb.py`:KB loader,双语合并,L1 引用约束(`is_known_id`)
  - `verbosity.py`:Mode(exec/learn/silent)枚举
  - `i18n.py`:zh/en/zh-en 切换
  - `explainer.py`:Explanation 渲染 + filter_refs(L1)+ verify_refs_async(L2)
  - `feedback.py`:用户回报(L3)落 `workspace/learning/feedback/`
- **路由器 schema 扩展**(`router/schema.py` DAGNode):`one_liner_zh/one_liner_en/why/theory_refs/alternatives` 字段
- **路由器 system prompt**:11 条 HARD RULES 加教学指令(KB id 必经 L1 过滤,unsure 留空)
- **CLI**:`tagent run --mode exec|learn|silent --lang zh|en|zh-en`
- **API**:`POST /run/text?mode=&lang=` query 参数
- **反幻觉**:实测 unknown-id 正确标记"该领域未收录,慎用"
- 版本 V1.3.0-alpha → V1.4.0-alpha

### Added(V1.3.0-alpha · Hermes-inspired 5 模块 + 跨项目精髓库 · 2026-05-11)

- **跨项目精髓库**:`D:/项目文件/_精髓库/`
  - `INDEX.md`:精髓库索引
  - `hermes-agent.md`:NousResearch/hermes-agent 完整精髓萃取(8 节,300+ 行;思想+模式+反模式+迁移 checklist)
- **5 新 runtime 模块**(派生 hermes 精髓):
  - `runtime/scheduler/`:定时任务(croniter + fcntl/msvcrt 双栈文件锁 + 运行时 prompt 注入扫描);`jobs.py / scheduler.py / injection_scan.py`
  - `runtime/subagent/`:并行子代理(ThreadPool 32 默认,resize 动态调整 + auxiliary LLM client 隔离 cache);`pool.py / aux_client.py / spawn.py`
  - `runtime/learning_loop/`:封闭学习循环(curator 闲置触发 + FTS5 跨会话搜 + 用户画像);`curator.py / session_search.py / user_model.py`;只归档不删
  - `runtime/backends/`:7 执行后端(`local/docker/ssh/singularity/modal/daytona/vercel_sandbox`);统一 `BaseExecutionEnv` 7 方法;Modal/Daytona 提供 serverless hibernate
  - `runtime/gateway/`:多平台 messaging(`telegram/discord/slack/wechat/feishu/dingtalk/email/webhook` 8 平台);统一 `Platform.send/configure`;`session.py` 跨平台对话连续
- **主宪章 §22**:Hermes-inspired 扩展能力章节(规则化);TOC 同步更新
- 版本 V1.2.0-alpha → V1.3.0-alpha

### Added(V1.2.0-alpha · M2 MCP 6 件套 + Web UI + 真模型路由 + 飞轮回灌 · 2026-05-11)

- **MCP 6 件套全部实现**(主宪章 §16):
  - `runtime/mcp/test_orchestrator/`:包装 runtime/router + orchestrator,5 工具(catalog/plan/run/status/report);Claude Code 可直接调用
  - `runtime/mcp/protocol_adapter/`:统一 ProtocolAdapter 抽象 + 5 起步 adapter(HTTP/gRPC/WS/MQTT/Kafka);HTTP 实测 ping 通过
  - `runtime/mcp/evidence_vault/`:证据归档 5 工具(upload_evidence/upload_evidence_path/list/get/search),MinIO + Postgres
  - `runtime/mcp/defect_tracker/`:工单桥 5 工具(create/get/update/query_bugs/list_trackers),默认 zentao + 预留扩展位(主宪章 §12 契约)
  - `runtime/mcp/knowledge_base/`:pgvector 向量检索 4 工具(embed/index_case/index_defect/search_similar),LiteLLM embedding + stub 兜底
  - `runtime/mcp/compliance_checker/`:行业合规规则 3 工具(list_profiles/get_profile/check_compliance);10 框架 profile 起步空载(SOC2/PCI-DSS/HIPAA/IEC 62304/IEC 61508/ISO 26262/DO-178C/GDPR/PIPL/CCPA)
  - 共享基类 `runtime/mcp/base.py`:make_server / run_stdio / @tool_decision_logged(决策落 `workspace/执行日志/decisions/` 符合主宪章 §18-12)
- **行业合规规则插槽** `profiles/compliance/`:10 框架空载示例 YAML,真规则由领域专家+test-lead 双签签字后入库
- **飞轮回灌路由**(M2-9):`runtime/router/retrieval.py` 历史相似用例 → LLM prompt few-shot;router 透明集成,无 KB 时降级
- **真模型路由测试套件**(M2-7):`runtime/tests/test_router_real.py` 20 样本(4 类型 × 5)真模型测试;门槛单模型 ≥85%、双模型投票 ≥95%;无 API key 自动 skip;失败自动落 decisions/ 含 seed+模型版本+输入快照(主宪章 §21 横切准则)
- **Web UI MVP**(M2-8):`runtime/web/` Vite+React 18+TypeScript+shadcn/ui+TanStack Query+React Router v7
  - 4 页:Upload(text/file/URL 三模式) / RunStatus(SSE 进度条) / Report(节点结果表) / Catalog(14 专家+14 skill)
  - §21 L2 必测项:Playwright E2E 7 用例(功能+边界+异常+兼容+可访问性);axe-core a11y 0 critical 门槛
  - 配套 vite 代理 `/api` → FastAPI(:8800)
- **`.mcp.json` 升级**:启用 `filesystem` + `test-orchestrator`;其他 5 件套写入 `_pending_servers_v1_2_0_alpha` 段供按需启用
- 版本 V1.1.0-alpha → V1.2.0-alpha

### Added(V1.1.0-alpha · 宪章合一 · darwin-skill 入库 · 2026-05-11)

- **主宪章扩展(memory `project_test_agent_workflow.md`)**:原 §0-§9 + How to apply 1-6 **字符级保留**;新增 §10-§20 仅承载规则/要求/约束(剔除示例/枚举/参考表):
  - §10 灵魂底色:三公理 + 五条铭文 + V1.0.0 锁死 + 双签解锁条件
  - §11 FULL_GUIDE.md 定位补充(优先级链:memory ＞ 私有源 ＞ FULL_GUIDE ＞ README)
  - §12 多 Bug Tracker(默认 zentao + 扩展位 `BugTrackerBase` 契约)
  - §13 按需安装 + 运行时补装铁律
  - §14 darwin-skill 自进化(棘轮 + Via Negativa 不消费运行数据)
  - §15 AgentChat 协作协议(test-lead 中枢 + 反问 3 级预算 + 争议未落档不签发)
  - §16 MCP 服务扩展位(6 件套 Phase 2)
  - §17 九大簇维度边界(认知地图;承认存在不假装能交付)
  - §18 测试架构 + 5 层门禁分层 + Flaky vs Reruns 哲学
  - §19 闭环约定 18 条(扩展 §8 质量闭环)
  - §20 Phase 触发条件(不绑月份)
  - How to apply 7-12 扩展项(铭文优先级 / 决策可追溯 / 纪要不可删 / darwin 棘轮 / 依赖补装反问 / 修改四关)
- **行业适配参照表全删除**(主宪章 + FULL_GUIDE 双删)
- **darwin-skill 入库**:`03-技能定义/darwin-skill/` 完整部署(SKILL.md + scripts/ + templates/ + assets/ + docs/),upstream 原文不改;13 Skill → 14 Skill
- **FULL_GUIDE.md 优化**:三公理/铭文 + 18 闭环段替换为"已迁主宪章 §X"指引(避免双份维护);Bug Tracker / 按需安装 / darwin / AgentChat 详节保留作为深度参考;附 runtime 章节(M1-11 留存)

### Added(V1.1.0-alpha · 运行时层)

- **新增 `runtime/` 运行时层**:把 14 专家 + 13 Skill + 49 脚本从"文档+工具箱"升级为"可执行运行时"。已有定义/Skill/脚本**保持不动**(宪章铁律),`runtime/` 仅作调度层。
  - `runtime/router/`:AI 路由(LiteLLM 多厂商:Claude/OpenAI/Gemini/Qwen/DeepSeek/Ollama)。被测物 → 专家+Skill DAG。含 stub provider 供 CI 离线测,准确率 5/5 类型(web/api/mobile/desktop/ai-model)
  - `runtime/registry/`:扫 `02-专家定义/*.md` + `03-技能定义/*.md` frontmatter 生成统一目录(14 expert + 13 skill,实测通过)
  - `runtime/orchestrator/`:**双轨**——Prefect 2.x flow(全功能,带 UI/重试/状态机)+ Direct 执行器(无 Prefect 也能跑,ThreadPoolExecutor 并发,降级方案)
  - `runtime/api/`:FastAPI 入口 `/run/text` `/run/file` `/run/url` `/status/{run_id}` `/report/{run_id}` `/catalog` `/health`。多格式上传 PDF/Word/MD/exe/APK/IPA/Docker/口头/URL/目录
  - `runtime/cli/`:Typer CLI `tagent run|plan|catalog|doctor`
  - `runtime/storage/`:飞轮 schema:Postgres+pgvector(向量检索),SQLAlchemy ORM(Run/Case/Defect/Evidence/Feedback/Embedding)+ Alembic 迁移 + MinIO 对象存储
  - `runtime/observability/`:OpenTelemetry trace + Loguru 结构化日志,run_id 全链路贯穿
  - `runtime/config/settings.py`:pydantic-settings 统一配置,`TAGENT_*` env 前缀
- **`runtime/docker-compose.yml`**:一键起 Postgres(pgvector)/MinIO/Prefect Server;可选 `--profile observability` 起 Tempo+Loki+Grafana
- **`runtime/Dockerfile`**:运行时镜像
- **`runtime/pyproject.toml`**:独立子包,声明 `tagent` 命令入口
- **路由验证**:5/5 类型(web/api/mobile/desktop/ai-model)stub 路由准确率 100%;E2E direct 模式 8 节点 DAG 跑通,run_id+耗时+脚本输出全记录
- **架构原则**:八维测试矩阵(平台/协议/类型/流程/自动化层/部署/Profile/智能等级)作为运行时元数据骨架;**行业 Profile 留扩展位**(`profiles/`,通用层做厚)

### Fixed(W3 收尾后发布前实测发现 2 bug)

- **web-demo Python 3.14 跑不通**：`greenlet`（playwright 依赖）尚无 Python 3.13/3.14 预编译 wheel，本地编译失败导致 `pip install` 失败、playwright 装不上、pytest 跑不到。修：`examples/web-demo/README.md` 显式标注 Python 3.11/3.12 推荐 + 加 venv 创建步骤 + 故障排查表新增 wheel 编译失败条目。
- **web-demo selector 失效**：`test_search_box_present` 用 `role=button[name='Search']` 不匹配 playwright.dev 当前 DOM 结构。修：换更稳定的 `text="Get started"`（hero CTA，多年不变）；`PlaywrightHomePage.has_search_button` → `has_get_started_link`；`test_search_box_present` → `test_get_started_link_present`。

修复验证：Python 3.11.9 + venv 重建后 `pytest -v` 输出 `2 passed in 2.33s`。

### Security（安全·上架前必修 Batch 1）

- **修复 `eval()` 远程代码注入风险**：`05-代码示例/media_validator.py` 中 `get_video_meta()` 原通过 `eval(video.get("r_frame_rate"))` 解析 FFmpeg 外部输出，存在注入风险。改用 `fractions.Fraction` 安全解析。
- **移除占位邮箱**：`SECURITY.md` 与 `CODE_OF_CONDUCT.md` 移除 `security@example.com` / `conduct@example.com` 占位地址，统一指向 GitHub Security Advisories 私密通道；避免上架后被误用作真实联系方式。
- **示例脱敏**：
  - `02-专家定义/13-系统集成测试.md` 示例中 `SSHClient(host="192.168.1.100", user="root", password="...")` 改为 `os.getenv()` 读取，配合 `.env` 注入；同段 `IOT_SSH_HOST` 占位改为 `<DEVICE_IP>`。
  - `02-专家定义/07-测试执行.md` 混沌命令示例中真实风格 IP `192.168.1.100` 改为占位 `<TARGET_IP>`。

### Changed（数字漂移修复 + URL 统一 Batch 2）

- **顶层文档数字一致性**：`8 位专家 / 9 agent / 8 skill / 12 utils` 等过时数字全栈修正为 `14 agent / 13 skill / 49 utils`（核心 8 专家 + 平台扩展 5 专家 + test-lead 协调者）。涉及：`README_DETAIL.md` / `01-快速开始/使用手册.md` / `02-专家定义/01-测试主管.md` / `03-技能定义/test-coordinator.md` / `install.sh`。
- **GitHub 仓库 URL 统一**：所有引用 `YOUR-USER/Test-Agent工作流搭建` 的位置统一为 `Wool-xing/Test-Agent`（权威英文仓库名；中文 `Test-Agent工作流搭建` 仅作目录别名）。fork 用户可用 `TEST_AGENT_REPO_URL` 环境变量覆盖。涉及：`01-快速开始/部署说明.md` / `01-快速开始/使用手册.md` / `README_DETAIL.md`。
- **覆盖率口径统一为 ~95%**：原 `~99%` (README/README_DETAIL) vs `约 90%` (00-项目导航) 不一致，统一为 `~95%`，剩 5% 为高度专业合规领域（航空 DO-178C / 医疗 HIPAA / 工业控制 IEC61508）。

### Added

- 新建 `CHANGELOG.md` + `VERSION` 文件，启动语义版本管理。
- **W3 信息架构重塑**：
  - `README_DETAIL.md` 改名为 `FULL_GUIDE.md`（宪章§0 文件分发策略：README.md 简明入口 ≤ 200 行 / FULL_GUIDE.md 详细指南）
  - 新建 `01-快速开始/INDEX.md` / `04-配置文件/INDEX.md` / `06-CICD集成/INDEX.md`（宪章§3 每目录索引；02/03/05 已有 README.md 等价于 INDEX）
  - `README.md` 头加项目代号 `test-agent-team` + 版本 + License
  - `README.md` 删除三视角矩阵段（迁移至 FULL_GUIDE.md，避免双份维护）
  - `README.md` 行数从 240 降至 168 行
- **W3 安全增强**：
  - `49 个 utils .py` 文件头加 `# SPDX-License-Identifier: MIT`（合规标识）
  - `.pre-commit-config.yaml` 加 gitleaks hook（凭据扫描）
  - `.gitignore` 补漏：`.ruff_cache/` / `*.jtl` / `*.pem` / `*.key` / `*.crt` / `*.p12` / `*.pfx` / `*.jks` / `id_rsa` / `id_ed25519` / `coverage.xml` / `pip-wheel-metadata/`
- **W3 收尾 · 方法论沉淀（F'+J+K）**：
  - `CONTRIBUTING.md` 末尾追加：**同步铁律段**（联动改动清单速查 + 自动化保障）+ **RACI 协作矩阵浓缩版**（14 专家 × 35 测试维度，含责任边界冲突解决与质量门禁联动）
  - `FULL_GUIDE.md` 末尾追加：**测试架构合理性深度章节**（6 子节：金字塔 2024 现代版 / Shift-Left 7 层 / Shift-Right 9 层 / 可观测三柱 + 测试可视化 / 五层质量门禁 + Flaky vs Reruns 哲学 / 调整路径 Phase 2-4 落地点）
  - 新建 `examples/web-demo/`：8 文件最小可跑 Web 测试示例（pytest + Playwright + Page Object，演示 `https://playwright.dev`，5 分钟跑通）
  - `FULL_GUIDE.md:395` 漏修补救：`utils/*.py（12 个）` → `49 个，含 __init__.py`

### Notes

W1+W2+W3 合并提交：上架前必修安全 + 数字漂移修复 + URL 统一 + 信息架构重塑（FULL_GUIDE/INDEX/SPDX/gitleaks）。
后续 W4 博客 + Show HN 准备 待执行。

> 注：本仓库 GitHub Actions CI 已配 `permissions: contents: read` 最小权限（F3）；CodeQL 显式声明 per-job 权限。pre-commit 已含 `detect-private-key` + 私有源 MD 防护 + .env 防护 + 14/13/49 文件统计。

---

---

## [1.0.0] - 2026-05-10

### Added

- 14 测试专家 Agent（核心 9 + 平台扩展 5）
- 13 测试技能 Skill（通用 8 + 平台 5）
- 49 utils Python 工具模块
- GitHub Actions + Jenkins 双 CICD
- Dependabot 周扫描 + pip-audit/safety CVE 拦截
- 多格式 PRD 加载（md/pdf/docx/xlsx/zip/png/url/html/pptx）
- MCP filesystem 通道；zentao/wechat/feishu/dingtalk MCP 教程骨架
- install.sh 一键远程部署
- LICENSE (MIT) / SECURITY.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md
