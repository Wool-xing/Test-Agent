# Anthropic DevRel 主动联系 · 草稿

> **目的**：进入 Anthropic 生态视野；获得 Featured Blog / Cookbook PR 合入 / Showcase 收录
> **战略地位**：T3 调整阀 B（6 月无 Anthropic mention → 触发主动出击）
> **不要做的事**：不公开喊话 / 不要求 endorsement / 不假装是合作伙伴

---

## 联系对象优先级

| 角色 | 谁 | 平台 | 推荐顺序 |
|------|-----|------|----------|
| DevRel Lead | Alex Albert | X (@alexalbert\_\_) / LinkedIn | **首选** |
| Product / Claude Code | Eric Anderson | LinkedIn | 第二 |
| Cookbook 维护者 | Anthropic Cookbook repo（GitHub） | PR / Issue | 第三（与 1+2 并行） |
| CPO | Mike Krieger | LinkedIn | **不主动**（太高，需 DevRel 引荐） |
| 一般 Twitter @AnthropicAI | 官号 | X | 不私聊，但被 @ 时回复 |

---

## 渠道 1 · X（Twitter）DM · 给 Alex Albert

**为什么 X DM 优先**：
- Alex 公开活跃在 X
- 短文化适合"打招呼+给 link"
- 不像 LinkedIn 那样正式

### DM 草稿（短，~280 字符以内 1 条）

```
Hi Alex, I built Test-Agent — a Claude Code-native testing framework with
14 agent roles (test-lead orchestrating 8 core + 5 platform specialists).
Shipped V1.0 today, MIT.

Would love your feedback on the methodology fit for the ecosystem.

→ github.com/Wool-xing/Test-Agent
```

**字符核对**：276 字符 ✓

**变体 A**（如不想用"feedback"被认为索要 endorsement）：

```
Hi Alex, just shipped Test-Agent — an Agent-Native testing framework
using Claude Code. 14 agents + 13 skills + 49 utils, MIT licensed.

If it fits your "Built with Claude" criteria, would be honored.

→ github.com/Wool-xing/Test-Agent
```

**变体 B**（如想突出工程深度）：

```
Hi Alex, Test-Agent went live today — a full testing framework with
14 specialized Claude Code agents covering Web/API/Mobile/Desktop/IoT/AI/LLM,
plus 49 Python utils for 20+ protocols.

Open to chat about Claude Code patterns we learned the hard way.

→ github.com/Wool-xing/Test-Agent
```

**我推荐**：变体 A——不索要 endorsement，但开口"Built with Claude"为 Anthropic 提供 showcase 接口。

---

## 渠道 2 · LinkedIn InMail · 给 Alex Albert + Eric Anderson

**为什么 LinkedIn 第二**：
- 正式渠道，留底
- InMail 一封要 credit，慎用
- 适合"长篇背景介绍"

### InMail 草稿 · 给 Alex Albert · ~150 字

```
Subject: Built Test-Agent on Claude Code — Agent-Native Testing Framework

Hi Alex,

I'm Wool, full-time on Test-Agent for the past quarter — an open-source
testing framework that treats AI agents as orchestrators rather than
assistants. The architecture:

- 14 agents (8 core + 5 platform: mobile/desktop/visual/IoT/AI-LLM)
- 13 skills, 49 Python utils, 20+ protocols
- Layered quality gates (smoke 95%/regression 90%/perf P95)
- 5-min web-demo to validate without full deploy
- MIT, no vendor lock-in

I'd love feedback on whether the methodology fits the Claude Code
ecosystem direction, and how to engage productively (Cookbook PR?
Featured Blog? Discord channel?).

GitHub: github.com/Wool-xing/Test-Agent

Best,
Wool
```

### InMail 草稿 · 给 Eric Anderson（更聚焦 Claude Code 产品角度）

```
Subject: Pattern feedback - Claude Code as test team orchestrator

Hi Eric,

Quick context: I built Test-Agent (github.com/Wool-xing/Test-Agent) —
a testing framework where Claude Code orchestrates 14 specialized agents.
Going through MIT, ~95% coverage, all platforms.

Beyond just promoting it, I'd value 30 min on:
- Patterns that worked vs broke when scaling Agent + Skill across 14 roles
- MCP usage observations (we kept it to filesystem only, used SDKs for
  notifications/Bug — happy to share the rationale)
- Roadmap priorities you'd find most useful (the Agent SDK adapter we're
  planning for Phase 4)

Open to async or call, your preference.

Best,
Wool
```

---

## 渠道 3 · Anthropic Cookbook · GitHub PR

**为什么 PR 渠道**：
- 留 commit history，official 合入即 endorsement
- Cookbook 维护者审 PR 时会看 repo——传播路径
- 比 DM 更"产品"，少社交压力

### Cookbook PR 路径

1. fork `anthropics/anthropic-cookbook` 或 `anthropics/claude-cookbooks` repo
2. 加目录 `examples/test-agent/`
3. 内容：
   - `README.md`：100-200 字介绍 + 链接
   - `agent-orchestration-pattern.ipynb`：用 Claude API 演示 test-lead 路由逻辑（精简版，不依赖 Test-Agent repo）
   - `skill-composition.ipynb`：演示 8 个核心 Skill 的组合方式
4. 在 PR description 附上 Test-Agent repo 链接 + Show HN 链接（如已发）

### PR description 草稿

```markdown
## Add Test-Agent · Agent-Native Testing Framework example

This PR contributes two notebooks demonstrating how to build a
testing-oriented agent team with Claude Code:

1. `agent-orchestration-pattern.ipynb` — test-lead pattern for
   coordinating 8+ specialized agents based on PRD keyword routing
2. `skill-composition.ipynb` — composing smoke / regression / coordinator
   skills with shared quality-gate state

Both are derived from Test-Agent (open source, MIT):
github.com/Wool-xing/Test-Agent

Patterns shown:
- Multi-agent orchestration with Claude as the bus
- Layered quality gates as decision input to the agent
- MCP filesystem channel + SDK direct calls (vs. all-MCP approach)
- Auto-routing PRD format detection (md/pdf/docx/exe/apk/...)

Open to feedback on the structure / which patterns to highlight more.
```

---

## 时机选择

| 渠道 | 何时发 | 为何 |
|------|--------|------|
| X DM Alex | **博客 + Show HN 发完后 24h 内** | 让他能看到外部对项目的反应（不是冷启动 spam） |
| LinkedIn Alex + Eric | X DM 后 48h，无回复时 | 不要并发轰炸 |
| Cookbook PR | **博客发完同时**，作为"成熟度证据" | 写 PR description 时引用博客 |

**关键原则**：先有外部声量（博客 + HN 评论 + 几 star），再敲 Anthropic 门。否则是冷启动 spam。

---

## 不要做的事

- ❌ 不要在 Twitter 公开 @Anthropic 喊话求 endorsement（廉价感）
- ❌ 不要在多个渠道 24h 内同时发（被认为 spam）
- ❌ 不要在邮件/DM 里写"我们"（除非有 co-maintainer）
- ❌ 不要假装是合作伙伴（不诚实，被发现毁牌）
- ❌ 不要在 DM 里写超过 280 字（短才有回复率）
- ❌ 不要发完没回复就再发（等 1 周再轻轻 follow up）
- ❌ 不要把 Anthropic 提及作为 README 主卖点（喧宾夺主）

---

## 期望管理（你心理预期）

- 50% 概率：完全没回复（DevRel inbox 巨量）→ 正常，1 周后 follow-up 1 次即可
- 30% 概率：有回复，回话术化感谢（"thanks for sharing"）→ 仍是成功，后续可以"我们更新了 X，您有兴趣..."
- 15% 概率：进一步对话或邀约 chat → 这是大成功，准备好 30 min 内容
- 5% 概率：Cookbook 合入 / Featured Blog → 跑路线图 Phase 4 决策门 G4

**6 个月内任一概率以上发生 = T3 调整阀 B 不触发**（不需要"急转直下"行动）。

---

## Follow-up 节奏（如无回复）

- Day 0：发首发 DM / PR
- Day 7：如无回复，**X 主页发一条 tweet**（不是 @Anthropic，是 nature post）展示 Test-Agent 新进展
- Day 14：如无回复，发 LinkedIn InMail（不同渠道）
- Day 30：如无回复，**写一篇博客**"What I learned building Claude Code agents"——客观技术分享，无任何索要
- Day 60：如无回复，参加 Anthropic Discord / 任何在线活动，**自然接触**（不主动 DM 同人）
- Day 90：如无回复，T3 阀 B 触发，重审"Anthropic 生态卡位"是否仍是 Phase 4 目标

---

## 一句话哲学

> 主动联系 Anthropic 不是为了"被 Anthropic 看到"，是为了"让 Anthropic 觉得我们在帮他们做事"。后者会主动 reach out，前者不会。
>
> 
