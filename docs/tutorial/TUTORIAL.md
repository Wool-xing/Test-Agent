# Test-Agent 5 步入门教程

> 目标：从零到跑通第一个 AI 驱动的端到端测试。预计 10 分钟。

## 前置

- Python 3.10+
- Git
- 一个 LLM API key（Claude / OpenAI / DeepSeek / Qwen 均可）

## Step 1: 安装（2 分钟）

```bash
git clone https://github.com/Wool-xing/Test-Agent.git
cd Test-Agent
pip install -e runtime/
```

验证安装：

```bash
tagent --version
# → Test-Agent Runtime v1.x.x
```

## Step 2: 初始化（1 分钟）

```bash
tagent init --preset minimal
```

生成 `.env` 和 `tagent.yml`。编辑 `.env` 填入你的 LLM API key：

```ini
TAGENT_LLM_PROVIDER=deepseek
TAGENT_LLM_API_KEY=sk-your-key-here
TAGENT_LLM_MODEL=deepseek-chat
```

可选：`TAGENT_LOG_LEVEL=DEBUG` 查看详细日志。

## Step 3: 冒烟自检（1 分钟）

```bash
tagent doctor --agents
```

验证 16 expert agents 全部就绪。输出类似：

```
✓ agents/01-测试主管.md            test-lead
✓ agents/02-需求分析.md            requirements-analyst
... (16 agents total)
```

## Step 4: 第一次 Demo（3 分钟）

```bash
tagent demo -y
```

这条命令跑一个完整的内置测试流程：
1. 用 fixture PRD（虚构的 SaaS 登录模块）
2. 16 agent 编排成 DAG
3. stub LLM 模拟执行（0 API 费用）
4. 产出测试用例 Excel + Word 报告 + Bug 草稿

输出示例：

```
Step 1/4 · tagent init --preset minimal
Step 2/4 · tagent doctor --agents
Step 3/4 · tagent selftest --e2e (16 agent DAG · stub LLM · 0 cost)
  ✓ DAG executed: 9/9 ok (100%)
Step 4/4 · Artifacts
  · workspace/测试用例/testcases_sample.xlsx
  · workspace/测试报告/测试报告_*.docx
  · workspace/测试报告/bug_drafts.json

✓ demo done
```

## Step 5: 真 LLM 跑你自己项目（3 分钟）

```bash
# 用你自己的 PRD
tagent run --prd docs/my-feature.md

# 或用在线文档
tagent run --prd https://your-wiki.com/prd/page

# 看结果
tagent report
```

在浏览器看 Dashboard：

```bash
tagent serve
# → http://127.0.0.1:8800/dashboard
```

## 进阶

- `tagent readiness --smoke 0.95 --regression 0.88 --perf-ok --security-ok` — 发布就绪评分
- `tagent selftest --e2e` — 全链路自检
- `tagent catalog` — 查看所有 experts + skills
- `tagent --help` — 完整命令列表

## 遇到问题？

1. 加 `--debug` flag 看详细日志
2. 跑 `tagent doctor` 检查环境
3. 看 `workspace/执行日志/` 下的 JSON/XML 产物
4. GitHub Issues: https://github.com/Wool-xing/Test-Agent/issues
