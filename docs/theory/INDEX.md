# Theory KB 索引(主宪章 §23 教学层准则)

> Test-Agent 部署后的**学习知识库**。用户进入学习模式时,Agent 依此 KB 提供权威解释。
> 主宪章 §23 铁律:**LLM 不得编造 KB 外的引用**(防幻觉 L1 层)。

## 双语支持

- 每张卡同时含 `xxx.zh.md` + `xxx.en.md`
- `--lang zh-en` 双栏对照(学英文用)
- UI i18n 独立(`runtime/web/src/locales/`)

## 12 大类(主宪章 §23)

| # | 分类 | 目录 | 主题示例 |
| --- | ------ | ------ | --------- |
| 1 | 工具使用 | [`01-tools/`](01-tools/INDEX.md) | pytest / Playwright / JMeter / Appium / Burp / Allure / k6 |
| 2 | 代码编程 | [`02-coding/`](02-coding/INDEX.md) | pytest fixture / async / typing / mock / Page Object / 设计模式 |
| 3 | 测试基础理论 | [`03-foundation/`](03-foundation/INDEX.md) | ISTQB / V 模型 / 金字塔 / Boehm 法则 / 七原则 |
| 4 | 测试策略 | [`04-strategy/`](04-strategy/INDEX.md) | 基于风险 / SBTM / Shift-Left / Shift-Right / 灰度 |
| 5 | 用例设计方法 | [`05-methods/`](05-methods/INDEX.md) | 等价类 / 边界值 / 判定表 / 状态迁移 / 配对 / 正交 |
| 6 | 协议认知 | [`06-protocols/`](06-protocols/INDEX.md) | HTTP/HTTPS / gRPC / WS / MQTT / Kafka / WebRTC / QUIC |
| 7 | 平台架构 | [`07-platforms/`](07-platforms/INDEX.md) | Web / 移动 / 桌面 / 嵌入式 / Serverless / Edge |
| 8 | 质量门禁 | [`08-gates/`](08-gates/INDEX.md) | smoke / regression / perf / Flaky / SLO / DORA |
| 9 | 安全测试 | [`09-security/`](09-security/INDEX.md) | SAST / DAST / 渗透 / Fuzz / 红蓝紫队 / OWASP Top 10 |
| 10 | AI 测试 | [`10-ai-testing/`](10-ai-testing/INDEX.md) | 幻觉 / Prompt 注入 / 漂移 / 对抗 / 越狱 / 公平性 / XAI |
| 11 | 行业合规 | [`11-compliance/`](11-compliance/INDEX.md) | SOC2 / PCI / HIPAA / IEC 62304 / IEC 61508 / ISO 26262 / DO-178C |
| 12 | 流程文化 | [`12-process/`](12-process/INDEX.md) | TDD / BDD / ATDD / RACI / RCA / 缺陷生命周期 |

## 权威源

详见 [`_authority_sources.yaml`](_authority_sources.yaml) 白名单:
- 国际:ISTQB / IEEE / ISO/IEC / NIST / OWASP / MITRE / Google / Microsoft / Martin Fowler / arXiv / ICSE / ISSTA
- 中国:GB/T 25000 / 等保 2.0 / 阿里 / 腾讯 / 美团 / 字节 / CCF / 软件学报
- AI:Hugging Face / Anthropic / OpenAI Evals / DeepEval
- 经典书目:Beizer / Myers / Crispin / Kaner / Stuttard 等

## 卡片 schema

详见 [`_schema.yaml`](_schema.yaml)。每卡含:
- `id` `category` `level`(基础/中级/高级)
- `name_zh` `name_en` + `one_liner_zh`(≤30 字,执行模式只输出此字段)
- `authority`(白名单中选 + 章节号)
- `confidence`(high/medium/low/**llm-draft-unreviewed**)
- `last_reviewed` + `reviewer`

## 反幻觉 3 层(主宪章 §23)

| 层 | 机制 |
| ---- | ------ |
| **L1 引用约束** | LLM 在 learn mode 只能引用 KB 中存在的 `id`;否则输出"该领域未收录,慎用" |
| **L2 自检循环** | LLM 生解释后,二次校验"引用的章节是否真存在 KB" |
| **L3 用户回报** | learn mode 末尾"👎 标记错误"→ 落 `workspace/learning/feedback/` |

## 累积规则(Q2 持续累积)

- **初始种子**:按项目用到的工具 / 协议 / 理论自动派生(M4-2)
- **执行新工具**:用户首次 `tagent run "测 X 协议"` 触发未收录 → 自动产 `llm-draft-unreviewed` 卡 → 待审
- **darwin-skill 联动**:darwin 周期扫 KB,优化卡内容
- **用户贡献**:PR 入库 → 自动加 `reviewer: community-PR-#xxx`

## 卡片产出策略(Q1-C+D)

1. **C 路径**:从 `_authority_sources.yaml` 白名单材料压缩
2. **D 路径**:LLM 生草稿 + 标 `confidence: llm-draft-unreviewed` 待审
3. 用户审完 → 改 `high/medium/low` + 填 `reviewer/last_reviewed`
