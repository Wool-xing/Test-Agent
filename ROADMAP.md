# Test-Agent V1.x ROADMAP

> 项目终态目标:每个 expert 真 LLM-driven / script-backed 实装,**绝不输出 mock 数据**。
> 当前状态:V1.14.0-alpha — 10 expert active,6 expert 处于 V1.x rollout。

## 当前活跃 expert (10 / 16)

### 5 真 LLM-driven (已上线)

| Expert | 职责 |
|--------|------|
| `test-lead` | 测试主管,需求分析 → 测试策略 → 路由分发 |
| `requirements-analyst` | 需求分析(PRD 多格式加载 + 路由建议) |
| `automation-engineer` | Web/API 脚本编写 + 性能测试编排 |
| `test-executor` | 测试执行与监控 |
| `bug-manager` | Bug 提交与追踪 |

### 5 script-backed (已上线)

| Expert | 工具栈 |
|--------|--------|
| `testcase-designer` | Excel 输出测试用例 |
| `data-preparer` | Faker 生成 + 脱敏 |
| `report-generator` | Word 报告生成 |
| `desktop-tester` | pywinauto 桌面自动化 |
| `ai-tester` | eval-harness AI 模型测试 |

---

## V1.x rollout — 6 expert LLM-driven minimum viable 实装路线

**节奏**: 一周 1 expert,共 6 周。每完成 1 个,active 数字 +1,README 同步。
**前置**: V1.15 Day 0 — runtime/router 防 mock 改造(拒绝未实装路由,返回明确错误)。
**完成标准**: 每 expert 接 LLM 真调用 + 结构化输出(markdown/JSON),通过 3 个测试 prompt 验证。

| # | Expert | LLM-driven 实装范围(minimum viable) | 目标版本 | 状态 |
|---|--------|------------------------------------|---------|------|
| 0 | (前置) runtime/router 防 mock | router 检测未实装 expert,返回明确错误,不输出 mock | V1.15.0-alpha 启动 | planned |
| 1 | `env-manager` | LLM 读 PRD → 环境检查清单 + 准备步骤 markdown | V1.15.0-alpha | planned |
| 2 | `mobile-tester` | LLM 读 PRD + Android/iOS 上下文 → 移动测试用例 + ADB/Xcode 命令清单 | V1.16.0-alpha | planned |
| 3 | `visual-tester` | LLM 读 PRD + UI 描述 → 视觉测试点 + Playwright 视觉对比脚本 | V1.17.0-alpha | planned |
| 4 | `system-tester` | LLM 读 PRD + IoT/串口/MQTT 上下文 → IoT 测试用例 + 命令清单 | V1.18.0-alpha | planned |
| 5 | `pentest-tester` | LLM 读 PRD + 授权检查通过 → 渗透测试计划 + 工具调用清单(生成计划,不执行攻击) | V1.19.0-alpha | planned (需 SECURITY.md 武器化代码授权 wiring 实装) |
| 6 | `automotive-tester` | LLM 读 PRD + CAN-bus/ISO-26262 上下文 → ASIL 评估 + HIL 测试用例 | V1.20.0-alpha | planned |

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

**每个 expert 实装完成前,runtime/router 拒绝路由该 expert,返回明确"未实装"错误**。

**绝不输出 mock 数据糊弄用户。**

V1.15 Day 0 启动 router 防 mock 改造前,V1.14.0-alpha 用户:
- 路由 6 个 in-rollout expert 时会**收到明确说明**,而非伪装成"已运行"的 mock 输出
- 详情见 [02-专家定义/01-测试主管.md](02-专家定义/01-测试主管.md) 路由表注释

---

## 进度跟踪

| 版本 | 日期 | 完成项 | active expert 数 |
|------|------|--------|----------------|
| V1.14.0-alpha | 2026-05-13 | bundle1 信任+法律线修复;ROADMAP.md 起步 | 10/16 |
| V1.15.0-alpha | TBD | router 防 mock + env-manager LLM-driven minimum viable | 11/16 |
| V1.16.0-alpha | TBD | mobile-tester LLM-driven minimum viable | 12/16 |
| V1.17.0-alpha | TBD | visual-tester LLM-driven minimum viable | 13/16 |
| V1.18.0-alpha | TBD | system-tester LLM-driven minimum viable | 14/16 |
| V1.19.0-alpha | TBD | pentest-tester LLM-driven minimum viable + 武器化授权 wiring | 15/16 |
| V1.20.0-alpha | TBD | automotive-tester LLM-driven minimum viable | 16/16 (V1.x rollout 完成) |
| V2.0.0 | TBD | V2.x 路线图启动:Skill Lifecycle 元工具改造 + 6 expert 深化 | 16/16 + V2 |
