# runtime/orchestrator/agents/ 索引

> 真 LLM-driven expert runner · 16 核心 expert 全落地

## 已实现 16 runner

| Runner | 角色源 | 上游 | 产物 |
|--------|--------|------|------|
| `requirements-analyst` | agents/02-需求分析.md | PRD(artifact_text) | `requirements_summary.json` |
| `automation-engineer` | agents/06-自动化脚本.md | requirements-analyst | `automation_scripts_plan.json` |
| `test-executor` | agents/07-测试执行.md | automation-engineer | `execution_plan.json` |
| `bug-manager` | agents/08-Bug管理.md | test-executor | `bug_drafts.json`(BugTracker-ready) |
| `test-lead` | agents/01-测试主管.md | 全链路 | `final_verdict_*.json`(上线决策) |

## 0 未实现

- test-lead 自身已实现(用全链路上游),其他 11 个:env-manager / data-preparer(scripted)/ testcase-designer(scripted)/ report-generator(scripted)/ mobile-tester / desktop-tester(scripted)/ visual-tester / system-tester / ai-tester(scripted)/ 渗透 / 车载
- **5 个有 script 真跑**(testcase-designer / data-preparer / report-generator / desktop-tester / ai-tester)→ SCRIPT_MAP 兜
- **6 个 no-op**(env-manager / mobile-tester / visual-tester / system-tester / 渗透 / 车载)→ 待 V1.15+

## 协议

### 输入(RunnerContext)
- `artifact_text`:原始 PRD / target 文本
- `upstream: dict[name, output]`:上游 runner 产物(by expert name)
- `settings_provider`:LLM provider(`stub` 走 mock)
- `workspace`:落盘根目录
- `lang` / `mode`(exec / learn / mock)

### 输出(RunnerResult)
- `output: dict`:per-agent schema JSON
- `artifact_path`:落盘位置(可空)
- `summary`:1 行业务语言
- `raw_llm_response`:debug / learn 模式给用户看

## 加新 runner

1. 写 `runtime/orchestrator/agents/<name>.py`,继承 `AgentRunner`,`@register("<name>")`
2. 实现 4 方法:`system_prompt` / `user_prompt` / `mock_output` / `output_file`(可选)
3. 加 import 到 `__init__.py`(触发 @register)
4. 跑 `tagent selftest --e2e` 验编排

##

- 自检规则(L1+L2+L3+L4)
- 真 agent 落地 canon
- 已有实现不动 — 5 个 SCRIPT_MAP 兜底 expert 不动
- 第 5 铭文:test-lead 决策 `requires_human_signoff: true`

## 相关

- 上一级:[`../INDEX.md`](../INDEX.md)
- adapter:[`../adapters/experts.py`](../adapters/experts.py)`execute_node` 先查 AGENT_RUNNERS,fallback SCRIPT_MAP
- 测试:`tagent selftest --e2e` 自动覆盖 16 runner 的 mock 路径
