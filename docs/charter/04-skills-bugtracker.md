<!--
本文件由 `FULL_GUIDE.md` 拆分而来 (W7-d 文档重构, 2026-05-14)。
原始单文件 1252 行 → 7 子文件; 主 FULL_GUIDE.md 改为索引。
内容与原 FULL_GUIDE.md 对应段完全一致, 仅拆不动语义。
-->

## 🧬 Skills 自进化机制（darwin-skill 集成）

> **不发明轮子**：直接采用上游 [darwin-skill](https://github.com/alchaincyf/darwin-skill) 的 SKILL.md，只在外围加触发 hook 和落点路径。本节定义集成边界，不复制 darwin 的内部规则。

### 1. 集成方式

```text
.claude/skills/darwin-skill/
  ├── SKILL.md                       ← 上游原文，禁止本地修改（防失同步）
  ├── templates/result-card*.html    ← 上游成果卡片模板
  └── scripts/screenshot.mjs         ← 上游截图脚本
workspace/执行日志/skill-evolution/
  ├── results.tsv                    ← 9 列优化日志（含 eval_mode）
  ├── test-prompts/{skill}.json      ← 每个 skill 的实测 prompt 集
  └── result-cards/                  ← 成果卡片 PNG 归档
```

**版本约定**：darwin-skill SKILL.md 来源于 upstream，每季度同步一次；不接受本地修改 fork（如需扩展，开 PR 给 upstream）。

### 2. 触发时机

| 触发方式 | 频率 | 操作者 |
|---------|------|--------|
| 用户手动 | 任意 | `> /darwin-skill` 或自然语言"优化所有 skills" |
| 定时（CI 月度） | 每月 1 日 | GitHub Actions schedule job，仅跑 baseline 不自动改 |
| 新 skill 入库后首测 | 一次性 | 新增 skill 在 .claude/skills/ 后，下次 darwin 跑必扫描 |

**默认不开自动改**——只跑 baseline 评分；改进必须人类确认（继承 darwin 的 Phase 2 人在回路）。

### 3. 评分维度（沿用 darwin 8 维 100 分制）

结构 60 分（静态）+ 效果 40 分（实测，含子 agent 跑测试 prompt）。详见 `.claude/skills/darwin-skill/SKILL.md` Rubric 节。

### 4. 棘轮纪律（与本项目门禁哲学一致）

- 改进后总分必须**严格高于**改进前才保留
- 退步 → 自动 `git revert`，不留烂代码
- 不能跑子 agent 时降级 `dry_run` 标注，**不静默跳过**
- 优化后 SKILL.md ≤ 原文 150% 体积，防膨胀

### 5. 与 AgentChat 的关系

darwin-skill 跑出的改进建议**不绕过协作协议**——重大改动（如 test-lead skill 本身）需走讨论触发，由 test-lead 协调 review 后再合入。

### 6. 不做的事（Via Negativa 显式标注）

V1.0.0 darwin-skill **不消费**项目运行数据（`discussions/` / `decisions/` / `history/` / `skill-evolution/results.tsv` 之外的运行历史），仅对 skill 文本结构本身做静态 + 实测评分优化。

**为什么不做"运行数据反哺 skill"的自学习闭环**：
1. 自学习难界定何时停止学习"坏样本"（如一段时期的高 flaky 反而被学进 skill 形成自我固化）
2. 数据驱动的 skill 改动违反"棘轮 + 人在回路"哲学——人类失去 review 节点
3. 第三公理"不可测之物必须被命名"——我们不假装能让 skill 自动学会"质量直觉"

**未来开案条件**：若需要开放自学习能力，须由 test-lead + 独立伦理责任人**双签**立项，且必须包含：(a) 数据筛选规则 (b) 学习棘轮阈值 (c) 人类否决通道。**当前路线图不承诺。**

---

## 🐛 Bug Tracker 多适配器

> 禅道是默认，但不是唯一。bug-manager agent 通过 `BugTrackerBase` 抽象层接 5 套适配器，由 `.env` 的 `BUG_TRACKER` 字段选择。

### 1. 适配器矩阵

| 适配器 | 状态 | 配置字段 | severity 映射 |
|--------|------|---------|--------------|
| **zentao**（默认） | ✅ V1.0.0 | `ZENTAO_URL / ZENTAO_USER / ZENTAO_TOKEN` | severity 1=P0 / 2=P1 / 3=P2 / 4=P3 |
| **jira** | ✅ V1.0.0 | `JIRA_URL / JIRA_USER / JIRA_TOKEN / JIRA_PROJECT_KEY` | Highest=P0 / High=P1 / Medium=P2 / Low=P3 |
| **github** | ✅ V1.0.0 | `GITHUB_TOKEN / GITHUB_REPO` | label `priority:p0..p3` |
| **linear** | ✅ V1.0.0 | `LINEAR_API_KEY / LINEAR_TEAM_ID` | priority 1=P0 / 2=P1 / 3=P2 / 4=P3 |
| **webhook** | ✅ V1.0.0 | `BUG_WEBHOOK_URL`（POST JSON） | 调用方自定义 |

### 2. 切换方式

```bash
# .env
BUG_TRACKER=jira   # zentao / jira / github / linear / webhook
JIRA_URL=https://yourorg.atlassian.net
JIRA_USER=qa@yourorg.com
JIRA_TOKEN=xxx
JIRA_PROJECT_KEY=QA
```

`utils/bug_manager.create_bug_manager()` 工厂函数读取 `BUG_TRACKER` 实例化对应 adapter，bug-manager agent 代码不变。

### 3. 统一契约（所有 adapter 必须实现）

```python
class BugTrackerBase:
    def submit_bug(title, description, severity, attachments, reproduce_steps) -> bug_id
    def get_status(bug_id) -> {status, assignee, severity, last_updated}
    def add_comment(bug_id, comment, attachments)
    def link_testcase(bug_id, testcase_id)
    def query_open_bugs(filters) -> list[bug]
```

不实现 = 不能注册为 adapter。所有 adapter 走同一 severity 映射表（`utils/bug_severity_map.py`），保证跨 tracker 的 P0/P1 语义一致。

### 4. 多 tracker 并存（罕见场景）

允许同时启用多个：例如 GitHub Issues 走开源贡献者反馈、禅道走内部 QA。配置 `BUG_TRACKER=github,zentao`，bug-manager 按 Bug 标签路由。

---
