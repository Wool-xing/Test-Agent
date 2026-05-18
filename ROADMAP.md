# Test-Agent V1.x ROADMAP

> 项目终态目标:每个 expert / skill 真 LLM-driven / script-backed 实装,**绝不输出 mock 数据**。
> 当前状态:V1.36.0 (**expert rollout 收尾 + skill rollout 完成（16/16）**)
> - **expert 16/16 active**(11 production + 5 script);0 rollout。
> - **skill 30/32 active**(23 production + 7 script);0 rollout;2 暂为 V2 vision 方法论参考。
> - 3 meta-skill(nuwa-skill / darwin-skill / karpathy-guidelines)独立,工具属性,不在 32 业务 skill 数内。
> - **V1.21.0 新增 SkillRunner 基础设施** (`runtime/orchestrator/skills/` + `SKILL_RUNNERS` registry + `@register_skill` deco + `experts.py` kind=skill 接 runner),解锁 skill 层 LLM-driven 全 16 实装 (V1.21-V1.31)。

## 当前活跃 expert (16 / 16) — V1.x rollout 收尾

### 11 真 LLM-driven (已上线)

| Expert | 职责 |
|--------|------|
| `test-lead` | 测试主管,需求分析 → 测试策略 → 路由分发 |
| `requirements-analyst` | 需求分析(PRD 多格式加载 + 路由建议) |
| `automation-engineer` | Web/API 脚本编写 + 性能测试编排 |
| `test-executor` | 测试执行与监控 |
| `bug-manager` | Bug 提交与追踪 |
| `env-manager` | 环境检查清单 + 准备步骤(V1.15.0 minimum viable) |
| `mobile-tester` | 移动测试用例 + ADB/Xcode 命令清单(V1.16.0 minimum viable) |
| `visual-tester` | 视觉测试点 + 对比脚本片段 + 容差配置(V1.17.0 minimum viable) |
| `system-tester` | IoT/串口/MQTT 测试用例 + 命令清单 + 协议特定配置(V1.18.0 minimum viable) |
| `pentest-tester` | 5 攻击域渗透测试计划 + 工具清单 + PoC plan(V1.19.0 minimum viable;仅输出计划文本,真执行守护在 utils 层 env gate) |
| `automotive-tester` | ASIL 评估 + HIL 测试 + ADAS 场景 + OTA 升级 + 合规矩阵(V1.20.0 minimum viable;V1.x rollout 收尾) |

### 5 script-backed (已上线)

| Expert | 工具栈 |
|--------|--------|
| `testcase-designer` | Excel 输出测试用例 |
| `data-preparer` | Faker 生成 + 脱敏 |
| `report-generator` | Word 报告生成 |
| `desktop-tester` | pywinauto 桌面自动化 |
| `ai-tester` | eval-harness AI 模型测试 |

---

## 当前活跃 skill — 基础 (含 rollout 总计 30/32 active)

### 23 production (已上线，本节约 13 核心 + rollout 表 10)

| Skill | 类别 |
|-------|------|
| `tdd-workflow` | TDD 工作流 |
| `e2e-testing` | E2E 测试 |
| `automotive-test` | 车载主编排(V1.31.0 · automotive batch) |
| `automotive-can-bus-test` | CAN总线测试(V1.31.0) |
| `automotive-adas-scenario` | ADAS场景库(V1.31.0) |
| `automotive-ota-update-test` | OTA升级测试(V1.31.0) |
| `automotive-hil-loop-test` | HIL环路测试(V1.31.0) |
| `regression-test` | 回归测试 |
| `smoke-test` | 冒烟测试 |
| `testcase-design` | 用例设计 |
| `test-coordinator` | 测试流程编排 |
| `verification-loop` | 5-phase 验证循环 |
| `eval-harness` | LLM 评测编排(V1.27.0 · skill rollout #5) |

### 7 script-backed (已上线)

| Skill | 工具栈 |
|-------|--------|
| `ai-test` | eval-harness AI 模型测试(utils/ai_validator) |
| `data-preparation` | Faker / data_masking / jmeter CSV |
| `desktop-test` | desktop_driver(pywinauto / AppleScript) |
| `jmeter-script-gen` | JMeter JMX 生成 |
| `python-script-gen` | pytest 脚本生成(Playwright + requests) |
| `security-review` | OWASP Top 10 + SAST + 依赖 CVE |
| `zentao-bug-submission` | BugTracker adapter (默认禅道) |

---

## V1.x rollout — 6 expert LLM-driven minimum viable 实装路线

**节奏**: 一周 1 expert,共 6 周。每完成 1 个,active 数字 +1,README 同步。
**前置**: V1.15 Day 0 — runtime/router 防 mock 改造(拒绝未实装路由,返回明确错误)。
**完成标准**: 每 expert 接 LLM 真调用 + 结构化输出(markdown/JSON),通过 3 个测试 prompt 验证。

| # | Expert | LLM-driven 实装范围(minimum viable) | 目标版本 | 状态 |
|---|--------|------------------------------------|---------|------|
| 0 | (前置) runtime/router + orchestrator 防 mock | catalog 单源 frontmatter 解析;router._validate_against_catalog warn + 降 confidence;orchestrator.execute_node 硬拒 rollout/vision/unknown(returncode=2,绝不输出 mock);expert + skill 双 layer 覆盖 | V1.14.0+1 | **done** (PR X4) |
| 1 | `env-manager` | LLM 读 PRD → 环境检查清单 + 准备步骤 markdown | V1.15.0 | **done** (runtime/orchestrator/agents/env_manager.py) |
| 2 | `mobile-tester` | LLM 读 PRD + Android/iOS 上下文 → 移动测试用例 + ADB/Xcode 命令清单 | V1.16.0 | **done** (runtime/orchestrator/agents/mobile_tester.py) |
| 3 | `visual-tester` | LLM 读 PRD + UI 描述 → 视觉测试点 + Playwright 视觉对比脚本 | V1.17.0 | **done** (runtime/orchestrator/agents/visual_tester.py) |
| 4 | `system-tester` | LLM 读 PRD + IoT/串口/MQTT 上下文 → IoT 测试用例 + 命令清单 | V1.18.0 | **done** (runtime/orchestrator/agents/system_tester.py) |
| 5 | `pentest-tester` | LLM 读 PRD + 授权检查通过 → 渗透测试计划 + 工具调用清单(生成计划,不执行攻击) | V1.19.0 | **done** (runtime/orchestrator/agents/pentest_tester.py;仅输出计划文本,真执行守护已在 utils 层 `api_security_scanner.py` / `ai_adversarial.py` 用 TAGENT_PENTEST_AUTHORIZED env gate;法律责任在操作者侧,见 SECURITY.md L84) |
| 6 | `automotive-tester` | LLM 读 PRD + CAN-bus/ISO-26262 上下文 → ASIL 评估 + HIL 测试用例 | V1.20.0 | **done** (runtime/orchestrator/agents/automotive_tester.py;ASIL 评估 + test_cases + bus_test_plan + adas_scenarios + ota_plan + compliance_matrix 结构化 JSON;覆盖 ECU/ADAS/IVI/V2X 4 子系统 + 8 协议 + 8 合规标准。**V1.x rollout 收尾**) |

---

## V1.x rollout — 16 skill 实装路线（已全部完成）

**节奏**: skill rollout 起点 V1.21.0 (SkillRunner 基础设施 + pentest-coordinator 首落地);后续 1 skill / PR 推进。
**完成标准**: 每 skill 接 LLM 真调用 (mock_output schema 覆盖 + production 升级 + ALL_SKILL_RUNNERS 锁规则同步)。
**前置**: ~~runtime/router 防 mock 改造 + skill 路由按 `SKILL_IMPL_STATUS` frontmatter 过滤~~ **已完成 V1.14.0+1 (PR X4)** — registry parse frontmatter + orchestrator.execute_node 拒 rollout/vision/unknown skill (returncode=2)。
**基础设施**: **V1.21.0 完成** — `runtime/orchestrator/skills/__init__.py` + `SKILL_RUNNERS` registry + `@register_skill` deco + `experts.py` kind=skill 接 skill runner (放在 SCRIPT_MAP fallback 前)。

### 通用平台 4 skill

| Skill | 范围 | 关联 expert | 状态 |
|-------|------|-------------|------|
| `mobile-test` | Android/iOS + 小程序 自动化 | mobile-tester | **done** (V1.23.0 · runtime/orchestrator/skills/mobile_test.py) |
| `visual-test` | 图像识别 + OCR + SSIM 视觉回归 | visual-tester | **done** (V1.24.0 · runtime/orchestrator/skills/visual_test.py) |
| `system-test` | IoT/串口/MQTT/音视频/Jaeger/Kafka | system-tester | **done** (V1.26.0 · runtime/orchestrator/skills/system_test.py) |
| `eval-harness` | LLM 评测(pass@k / Jaccard / stability) | ai-tester(深化) | **done** (V1.27.0 · runtime/orchestrator/skills/eval_harness.py · 5 阶段编排 + 质量门禁 + 安全护栏) |

### Pentest 7 skill（已全部完成 · SECURITY.md 武器化授权 wiring 已实装）

| Skill | 范围 | 状态 |
|-------|------|------|
| `pentest-coordinator` | 渗透总编排(授权 → 侦察 → 漏洞 → 利用 → 报告) | **done** (V1.21.0 · runtime/orchestrator/skills/pentest_coordinator.py · 5 阶段编排 + authorization_check + subagent_pool + refuse_conditions) |
| `pentest-recon` | 侦察(被动+主动信息收集) | **done** (V1.25.0) |
| `pentest-vuln` | 漏洞发现(5 攻击域 + SAST/DAST) | **done** (V1.25.0) |
| `pentest-exploit` | 漏洞利用(沙箱 PoC,不真破坏) | **done** (V1.30.0 · pentest batch 2) |
| `pentest-api` | API 渗透(OWASP API Top 10 2023) | **done** (V1.30.0 · pentest batch 2) |
| `pentest-web` | Web 渗透(OWASP Top 10 + ASVS) | **done** (V1.30.0 · pentest batch 2) |
| `pentest-report` | 渗透报告(仅 working PoC 入报告,shannon 哲学) | **done** (V1.30.0 · pentest batch 2) |

### Automotive 5 skill

| Skill | 范围 |
|-------|------|
| `automotive-test` | 整车主编排(ECU + ADAS + IVI + V2X) | **done** (V1.31.0 · automotive batch) |
| `automotive-can-bus-test` | CAN/CAN-FD/LIN/FlexRay/SOME-IP | **done** (V1.31.0 · automotive batch) |
| `automotive-adas-scenario` | ADAS 场景库 + SOTIF(ISO 21448) | **done** (V1.31.0 · automotive batch) |
| `automotive-ota-update-test` | OTA 升级(UN R156 / GB 44496-2024) | **done** (V1.31.0 · automotive batch) |
| `automotive-hil-loop-test` | HIL/SIL/MIL/PIL 环路 | **done** (V1.31.0 · automotive batch) |

---

## V1.34-V1.36 能力扩展

- **V1.34**: script_bridge.py 桥接 5 独立脚本进 orchestrator pipeline
- **V1.35**: 11 深度审计模块 (flaky guard / API security v2 / data factory v2 / perf orchestrator / event harness / visual regression / ML prioritizer / differential tester / EU AI Act / supply chain)
- **V1.36**: 6 延期模块 (chaos v2 / state machine v2 / DB test v2 / BDD v2 / carbon scheduler / canary config) + CVE-2025-71176 fix + 深度审查65发现全修

---

## V2.x vision — 2 skill(暂留方法论参考形态)

| Skill | 当前形态 | V2 路线 |
|-------|----------|---------|
| `agent-introspection-debugging` | 方法论参考 | LLM 决策回放 + 工具调用透明化实装 |
| `build-your-own-x-explorer` | 教学引导参考 | 与 docs/theory/ 22 KB 卡片联动检索引擎 |

---

## V2.x 路线图 (longer-term)

### Skill Lifecycle 元工具改造 (适配测试领域)

- `nuwa-skill` → 测试 skill / agent 蒸馏器(改造输入域 + 蒸馏维度 + 输出模板)
- `darwin-skill` → 测试领域 8 维评分体系(重写评分维度对齐 Test-Agent 业务)

### 6 expert 深化(从 LLM-driven minimum viable → 完整 wiring)

- 接入真实工具调用(sqlmap / Burp / CAN-bus 库等)
- 自动化测试执行(不止生成计划,真跑)
- 与 marketplace 4-gate 集成
- 接入 darwin-skill 持续打分 + 周自检调度
- 接入 nuwa-skill 创建 CLI 入口 `tagent skill new <name>`

---

## 防 mock 承诺

**每个 expert / skill 实装完成前,runtime/router + orchestrator 拒绝路由,返回明确"未实装"错误**。

**绝不输出 mock 数据糊弄用户。**

V1.14.0+1 (PR X4) 起,双 layer 防 mock 已落地:
- **registry 单源**: catalog 解析 `02-专家定义/*.md` `EXPERT_IMPL_STATUS` + `03-技能定义/*.md` `SKILL_IMPL_STATUS` frontmatter,实装状态来源唯一
- **router 软警告**: `_validate_against_catalog` 检测 rollout / vision / unknown → 加 issues 并降 confidence 0.3
- **orchestrator 硬拒**: `execute_node` 对 expert / skill 任意 rollout / vision / unknown 返回 `returncode=2` + stderr "未实装",绝不走 no-op "documented step recorded" 假成功路径
- 用户路由 0 个 in-rollout expert / 0 个 in-rollout skill / 2 个 vision skill 时**收到明确说明**,而非伪装成"已运行"的 mock 输出
- 详情见 [02-专家定义/01-测试主管.md](02-专家定义/01-测试主管.md) 路由表注释

---

## 进度跟踪

| 版本 | 日期 | 完成项 | active expert 数 |
|------|------|--------|----------------|
| V1.14.0 | 2026-05-13 | bundle1 信任+法律线修复;ROADMAP.md 起步 | 10/16 |
| V1.14.0+1 | 2026-05-15 | X3 数字诚实化(README/ROADMAP)+ X4 防 mock 闭环 (registry 单源 frontmatter / router warn / orchestrator hard block expert+skill 双 layer) | 10/16 |
| V1.15.0 | 2026-05-15 | env-manager LLM-driven minimum viable (runtime/orchestrator/agents/env_manager.py;LLM 读 PRD → env_checks + prep_steps + dependencies + risks 结构化 JSON) | 11/16 |
| V1.16.0 | 2026-05-15 | mobile-tester LLM-driven minimum viable (runtime/orchestrator/agents/mobile_tester.py;LLM 读 PRD + Android/iOS 上下文 → test_cases + device_commands + mobile_specific 结构化 JSON) | 12/16 |
| V1.17.0 | 2026-05-15 | visual-tester LLM-driven minimum viable (runtime/orchestrator/agents/visual_tester.py;LLM 读 PRD + UI 描述 → visual_test_points + comparison_scripts + tolerance + baseline_strategy 结构化 JSON) | 13/16 |
| V1.18.0 | 2026-05-15 | system-tester LLM-driven minimum viable (runtime/orchestrator/agents/system_tester.py;LLM 读 PRD + IoT/串口/MQTT 上下文 → test_cases + device_commands + protocol_specific + test_environment 结构化 JSON;覆盖 IoT/audiovideo/tracing/mq/integration 5 类) | 14/16 |
| V1.19.0 | 2026-05-16 | pentest-tester LLM-driven minimum viable (runtime/orchestrator/agents/pentest_tester.py;LLM 读 PRD + 安全上下文 → test_mode + target_scope + recon/vuln/exploit/reporting phases 结构化 JSON;覆盖 5 攻击域 Injection/XSS/SSRF/Auth/Authz;仅输出计划文本,真执行守护在 utils 层 env gate;法律责任在操作者侧 SECURITY.md L84) | 15/16 |
| V1.20.0 | 2026-05-16 | automotive-tester LLM-driven minimum viable (runtime/orchestrator/agents/automotive_tester.py;LLM 读 PRD + CAN-bus/ISO-26262 上下文 → vehicle_subsystem + asil_assessment + test_cases + bus_test_plan + adas_scenarios + ota_plan + compliance_matrix + test_environment 结构化 JSON;覆盖 ECU/ADAS/IVI/V2X 4 子系统 + 8 协议 + 8 合规标准。**V1.x rollout 收尾**) | 16/16 expert (V1.x rollout 完成) |
| V1.21.0 | 2026-05-16 | **skill rollout 起点** — SkillRunner 基础设施 (runtime/orchestrator/skills/__init__.py + SKILL_RUNNERS registry + @register_skill deco + experts.py kind=skill 接 runner) + pentest-coordinator 首 skill 落地 (5 阶段编排 + authorization_check + subagent_pool + refuse_conditions). 解锁 14 rollout skill 后续流水线. | 16 expert + 8/32 production (15 rollout 待) |
| V1.22.0 | 2026-05-16 | **tagent config CLI** — 多模型 onboarding Step 2 (runtime/cli/config.py · 6 provider 内置 + 厂商配置 cookbook + use/set/unset/list/show 子命令). **多 provider 通用 env 通道** (LLM_PROVIDER + LLM_API_KEY + LLM_MODEL) + stub 扩 4 path. | 16 expert + 8/32 production |
| V1.23.0 | 2026-05-16 | **skill rollout #2** — mobile-test skill LLM-driven 生产落地 (runtime/orchestrator/skills/mobile_test.py · Android/iOS 双平台 + 小程序支持) | 16 expert + 9/32 production |
| V1.24.0 | 2026-05-16 | **skill rollout #3** — visual-test skill LLM-driven 生产落地 (runtime/orchestrator/skills/visual_test.py · Airtest + OCR + SSIM 视觉对比) | 16 expert + 10/32 production |
| V1.25.0 | 2026-05-16 | **skill rollout #4** — pentest-recon + pentest-vuln 双 skill LLM-driven 生产落地 (侦察: 端口/子域/服务指纹 + 漏洞: 5 攻击域 hybrid SAST+blackbox) | 16 expert + 12/32 production |
| V1.26.0 | 2026-05-16 | **skill rollout #5** — system-test skill LLM-driven 生产落地 (runtime/orchestrator/skills/system_test.py · IoT/音视频/追踪/消息队列 4 场景) | 16 expert + 13/32 production |
| V1.27.0 | 2026-05-16 | **skill rollout #6** — eval-harness skill LLM-driven 生产落地 (runtime/orchestrator/skills/eval_harness.py · pass@k / Jaccard@k / top-1 stability / latency 4 指标 + 安全护栏) | 16 expert + 14/32 production |
| V1.28.0 | 2026-05-16 | **skill rollout #7** — pentest-api + pentest-web 双 skill LLM-driven 生产落地 (API: OWASP API Top 10 + REST/GraphQL/gRPC/WebSocket · Web: OWASP Top 10 + ASVS + 2FA 自动登录) | 16 expert + 16/32 production |
| V1.29.0 | 2026-05-16 | **skill rollout #8** — pentest-exploit + pentest-report 双 skill LLM-driven 生产落地 (exploit: 沙箱内验证 PoC + 不可破坏性约束 · report: working PoC 嵌入 + CWE/CVSS/PoC/修复 4 维) | 16 expert + 18/32 production |
| V1.30.0 | 2026-05-16 | **skill rollout #9** — automotive-test + automotive-can-bus-test 双 skill LLM-driven 生产落地 (主编排: 10 阶段 HARA→报告 · CAN: CAN/CAN-FD/SOME-IP 协议一致性 + dbc 解析) | 16 expert + 20/32 production |
| V1.31.0 | 2026-05-16 | **skill rollout #10 (收尾)** — automotive-adas-scenario + automotive-ota-update-test + automotive-hil-loop-test 3 skill LLM-driven 生产落地 (ADAS: AEB/ACC/LKA + CARLA 仿真 · OTA: 6 校验 + UN R156/GB 44496 合规 · HIL: MIL/SIL/HIL 三环 + dSPACE). **V1.x rollout 完成 — 23/32 production + 7 script + 0 rollout + 2 vision.** | 16 expert + 23/32 production (0 rollout 待) |
| V1.32.0 | 2026-05-17 | 深审32发现全修 + 版本号全同步 + 私源泄漏清洗 | 16 expert + 23/32 production |
| V1.32.1 | 2026-05-17 | CONTRIBUTING skill count 33→32 fix + 版本号同步 | 16 expert + 23/32 production |
| V1.32.2 | 2026-05-17 | Security hardening batch: CWE-78 fix + credential removal + CORS + WebSocket leak + XML escape | 16 expert + 23/32 production |
| V1.32.3 | 2026-05-17 | Refactor: _stub_response dispatch table + fuzzer ALL_PAYLOADS hoist | 16 expert + 23/32 production |
| V1.32.4 | 2026-05-17 | Honesty pass: remove aspirational numbers + split overlong functions | 16 expert + 23/32 production |
| V1.32.5 | 2026-05-17 | Security: shell injection + hardcoded creds + silent failures | 16 expert + 23/32 production |
| V1.33.0 | 2026-05-17 | MASTER_PLAN 38/38 items across 8 phases complete | 16 expert + 23/32 production |
| V1.34.0 | 2026-05-18 | Phase 1-5 initial audit: 18 additions (settings/IDE/Docker/Prometheus/streaming/PBT/contract/schema fuzz/compliance/DORA) | 16 expert + 23/32 production |
| V1.35.0 | 2026-05-18 | Deep audit 11 core modules (flaky guard/API security v2/data factory v2/perf/e2e event harness/visual regression/ML prioritizer/differential/EU AI Act/supply chain) | 16 expert + 23/32 production |
| V1.36.0 | 2026-05-18 | Remaining 6 deferred modules + CVE-2025-71176 fix + 深度审查65发现全修 | 16 expert + 30/32 active (23 production + 7 script) |
| V1.37.0 | 2026-05-18 | Phase 2 charter closure: Bug 5适配器(YAML门禁+按需安装) + HIGH 2(H16/H18) + MEDIUM 4(M12/M14/M15/M19) + contract gate + utils tests | 16 expert + 30/32 active · Phase 2 complete |
| V1.38.0 | 2026-05-18 | Phase 3.1 伦理/偏见审计: fairness_auditor.py (dataset bias + 6 model fairness metrics + intersectional + decision audit) + 20 tests + ai_validator bias audit pipeline | 16 expert + 30/32 active · 1/3 Phase 3 done |
| V1.39.0 | 2026-05-18 | Phase 3.2 沉默故障检测: silent_failure_detector.py (threshold drift + Mann-Kendall + OLS trend + sliding window + multi-source batch) + 21 tests + tracing/web_vitals/prometheus collectors | 16 expert + 30/32 active · 2/3 Phase 3 done |
| V2.0.0 | TBD | V2.x 路线图启动 | 16/16 + V2 |
