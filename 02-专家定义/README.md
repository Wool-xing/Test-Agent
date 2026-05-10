# 02-专家定义 索引

14 个 Agent，分两类：核心通用流程 + 平台专项扩展。

> 顶层导航见根目录 `00-项目导航.md`。

---

## 类别 1：核心通用流程 9 Agent（每次测试必经）

| 序号 | Agent 文件 | 角色 | 主要产出 |
|------|-----------|------|---------|
| 01 | `01-测试主管.md` | **test-lead**（协调者） | 测试计划 / 路由决策 / 质量门禁 / 最终上线建议 |
| 02 | `02-需求分析.md` | requirements-analyst | requirements_analysis_*.md + JSON 摘要 |
| 03 | `03-用例设计.md` | testcase-designer | testcases_*.xlsx（4 Sheet） |
| 04 | `04-环境管理.md` | env-manager | 环境检查 JSON + Docker 编排 |
| 05 | `05-数据准备.md` | data-preparer | test_data.json + jmeter_users.csv |
| 06 | `06-自动化脚本.md` | automation-engineer | pytest UI/API 脚本 + 协调 JMeter |
| 07 | `07-测试执行.md` | test-executor | 执行结果 JSON + Allure + JMeter |
| 08 | `08-Bug管理.md` | bug-manager | 禅道 Bug ID 列表 + 日报 |
| 09 | `09-报告生成.md` | report-generator | Word 报告 + 三端通知 |

### 流程依赖关系

```
test-lead 协调
   ↓
requirements-analyst → testcase-designer → [并行] env-manager + data-preparer →
automation-engineer → /smoke-test → test-executor 功能 → test-executor 性能 →
bug-manager → report-generator → test-lead 决策
```

---

## 类别 2：平台专项扩展 5 Agent（按 PRD 形态路由）

| 序号 | Agent 文件 | 角色 | 触发条件（PRD 关键词） |
|------|-----------|------|----------------------|
| 10 | `10-移动测试.md` | **mobile-tester** | Android / iOS / .apk / .ipa / 微信小程序 / 支付宝小程序 |
| 11 | `11-桌面测试.md` | **desktop-tester** | .exe / Windows 桌面 / .app / macOS / Electron / VSCode / 钉钉PC |
| 12 | `12-视觉游戏测试.md` | **visual-tester** | 游戏 / Canvas / WebGL / Unity / Unreal / OCR / 视觉回归 |
| 13 | `13-系统集成测试.md` | **system-tester** | IoT / 嵌入式 / 串口 / MQTT / 音视频 / Jaeger / Kafka |
| 14 | `14-AI模型测试.md` | **ai-tester** | 模型 / AI / LLM / 推理 / 推荐算法 / fairness / 数据漂移 |

### 路由识别（自动）

`utils/prd_loader.suggest_agents(text)` 输出：
```json
{
  "platforms": ["mobile_android", "api"],
  "recommended_agents": ["mobile-tester", "automation-engineer"],
  "recommended_skills": ["/mobile-test", "/python-script-gen"]
}
```

由 test-lead 接收后编排核心 9 + 选定平台扩展。

---

## YAML frontmatter 规范

每个 agent 文件顶部必含：

```yaml
---
name: <agent-id>
description: <一句话职责描述>
tools: Read, Write, Bash, Grep, Glob   # 按需添加 Edit
---
```

`name` 是 agent ID，被 test-lead 用 SendMessage 调用 / `.claude/agents/` 加载。
`description` 决定 Claude Code 何时主动调用此 agent（关键词匹配）。

---

## 添加新 Agent

详见根目录 [`CONTRIBUTING.md`](../CONTRIBUTING.md) "添加新 Agent" 章节。
