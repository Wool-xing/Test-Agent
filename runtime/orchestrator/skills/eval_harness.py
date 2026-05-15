"""eval-harness skill · LLM 读上游 ai-tester 产物 → 4 维度 LLM/AI 评测编排.

V1.27.0-alpha minimum viable (ROADMAP skill rollout #5 落地):
- LLM 读 PRD + 上游 ai-tester expert 产物 → 5 阶段评测计划
  (评测配置 / pass@k / 稳定性 / 延迟 / 报告归档)
  + 质量门禁 + 安全护栏
- 不实装 03-技能定义/eval-harness.md 全部职责 (eval_replay.py 真跑
  / PII scrub 执行 / LongMemEval benchmark 等留后续深化)
- 输出评测计划 JSON, 真执行在 runtime/tutor/eval_replay.py + ai_validator.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register_skill


@register_skill("eval-harness")
class EvalHarness(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 eval-harness skill(03-技能定义/eval-harness.md)。\n"
            "职责:基于 PRD + 上游 ai-tester expert 产物,编排 LLM/AI 系统评测 5 阶段计划。\n"
            "原则:\n"
            "1) 识别评测目标:prompt 版本回归 / RAG retrieval 质量 / agent 路由准确率 / 模型升级对比\n"
            "2) opt-in 不偷数据:评测必显式 TAGENT_EVAL_CAPTURE=1, production 用户不意外累积\n"
            "3) PII 必 scrub:落档前 6 类正则 (email/phone/SSN/API-key/card/IP)\n"
            "4) 4 维度必覆盖:Jaccard@k(pairwise 相似度) / top-1 stability / latency Δ(P50/P95/P99) / pass@k\n"
            "5) 失败必复现:固定 seed + snapshot, 分布不只看 mean (必看 P50/P95/P99)\n"
            "6) off-by-default:评测框架不在 production 默认激活\n"
            "7) 黄金测试集优先:用户提供的 labeled dataset > 自动生成\n"
            "8) 安全护栏:越狱/对抗 prompt 评测仅在显式授权后运行\n"
            "输出严格 JSON,不要 markdown 代码块包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        req_summary = ctx.upstream.get("requirements-analyst", {})
        ai_plan = ctx.upstream.get("ai-tester", {})
        features = req_summary.get("features", [])
        eval_target = ai_plan.get("eval_target", "llm_application")
        test_cases = ai_plan.get("test_cases", [])
        golden_dataset = ai_plan.get("golden_dataset", "")
        model_version = ai_plan.get("model_version", "")
        return (
            f"## 原始 PRD(截断 3000 字符)\n```\n{ctx.artifact_text[:3000]}\n```\n\n"
            f"## 上游 requirements-analyst 摘要\n"
            f"- 功能数: {len(features)} (P0={sum(1 for f in features if f.get('priority') == 'P0')})\n\n"
            f"## 上游 ai-tester expert 产物\n"
            f"- 评测目标: {eval_target}\n"
            f"- 用例数: {len(test_cases)}\n"
            f"- 黄金测试集: {golden_dataset or '(未提供, 将自动生成 baseline)'}\n"
            f"- 模型版本: {model_version or '(未指定)'}\n\n"
            "## 输出 schema\n"
            "{\n"
            '  "project_name": "string,简短项目名",\n'
            '  "run_id": "string,UUID/timestamp 任务 id",\n'
            '  "eval_target": "llm_application|rag_system|agent_router|model_upgrade|prompt_regression|other",\n'
            '  "model_version": "string,当前模型版本",\n'
            '  "baseline_version": "string,基线模型版本(如有)",\n'
            '  "safety_checks": {\n'
            '    "opt_in_confirmed": true,\n'
            '    "pii_scrub_enabled": true,\n'
            '    "adversarial_authorized": false,\n'
            '    "seed_fixed": 42\n'
            "  },\n"
            '  "phases": [\n'
            '    {"phase": 1, "name": "eval_config", "estimated_min": 5, "config": {"capture_mode": "opt-in", "output_dir": "workspace/执行日志/eval/", "seed": 42, "k_samples": 10}, "depends_on": []},\n'
            '    {"phase": 2, "name": "pass_at_k", "estimated_min": 20, "cases": [{"test_id": "string", "prompt": "string", "expected": "string", "k": 10, "threshold": 0.7}], "depends_on": ["eval_config"]},\n'
            '    {"phase": 3, "name": "stability_check", "estimated_min": 15, "cases": [{"test_id": "string", "prompt": "string", "runs": 5, "metric": "top1_consistency|jaccard_k|semantic_equiv"}], "depends_on": ["eval_config"]},\n'
            '    {"phase": 4, "name": "latency_check", "estimated_min": 10, "cases": [{"test_id": "string", "endpoint": "string", "runs": 100, "metrics": ["p50_ms", "p95_ms", "p99_ms"]}], "depends_on": ["eval_config"]},\n'
            '    {"phase": 5, "name": "report_archive", "estimated_min": 5, "outputs": ["string,路径"], "depends_on": ["pass_at_k", "stability_check", "latency_check"]}\n'
            "  ],\n"
            '  "quality_gates": {\n'
            '    "pass_at_1_min": 0.70,\n'
            '    "jaccard_at_5_min": 0.60,\n'
            '    "top1_stability_min": 0.90,\n'
            '    "latency_p95_ms_max": 3000,\n'
            '    "latency_delta_pct_max": 20,\n'
            '    "pii_leak": 0\n'
            "  },\n"
            '  "outputs": {\n'
            '    "eval_dir": "workspace/执行日志/eval/",\n'
            '    "capture_dir": "workspace/执行日志/eval/captures/",\n'
            '    "replay_dir": "workspace/执行日志/eval/replays/",\n'
            '    "report_dir": "workspace/执行日志/eval/reports/",\n'
            '    "allure_dir": "workspace/Allure/eval/{run_id}/"\n'
            "  },\n"
            '  "risks": ["string,如 黄金集过小致 overfit / prompt 顺序敏感 / 非确定性模型 top-1 随机"],\n'
            '  "confidence": "high|medium|low"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:  # noqa: ARG002
        return {
            "project_name": "selftest-fixture",
            "run_id": "selftest-20260516-000005",
            "eval_target": "llm_application",
            "model_version": "claude-sonnet-4-6",
            "baseline_version": "claude-sonnet-4-5",
            "safety_checks": {
                "opt_in_confirmed": True,
                "pii_scrub_enabled": True,
                "adversarial_authorized": False,
                "seed_fixed": 42,
            },
            "phases": [
                {
                    "phase": 1,
                    "name": "eval_config",
                    "estimated_min": 5,
                    "config": {
                        "capture_mode": "opt-in",
                        "output_dir": "workspace/执行日志/eval/",
                        "seed": 42,
                        "k_samples": 10,
                    },
                    "depends_on": [],
                },
                {
                    "phase": 2,
                    "name": "pass_at_k",
                    "estimated_min": 20,
                    "cases": [
                        {"test_id": "func-001", "prompt": "Write a function that reverses a linked list", "expected": "reverses linked list in O(n)", "k": 10, "threshold": 0.7},
                        {"test_id": "func-002", "prompt": "Implement binary search in Python", "expected": "O(log n) search on sorted array", "k": 10, "threshold": 0.7},
                        {"test_id": "func-003", "prompt": "Write SQL to find duplicate emails", "expected": "GROUP BY HAVING COUNT > 1", "k": 10, "threshold": 0.6},
                    ],
                    "depends_on": ["eval_config"],
                },
                {
                    "phase": 3,
                    "name": "stability_check",
                    "estimated_min": 15,
                    "cases": [
                        {"test_id": "stab-001", "prompt": "Explain transformer attention mechanism", "runs": 5, "metric": "jaccard_k"},
                        {"test_id": "stab-002", "prompt": "What is the capital of France?", "runs": 5, "metric": "top1_consistency"},
                        {"test_id": "stab-003", "prompt": "Summarize: AI safety is important because...", "runs": 5, "metric": "semantic_equiv"},
                    ],
                    "depends_on": ["eval_config"],
                },
                {
                    "phase": 4,
                    "name": "latency_check",
                    "estimated_min": 10,
                    "cases": [
                        {"test_id": "lat-001", "endpoint": "llm-completion", "runs": 100, "metrics": ["p50_ms", "p95_ms", "p99_ms"]},
                        {"test_id": "lat-002", "endpoint": "rag-retrieval", "runs": 100, "metrics": ["p50_ms", "p95_ms", "p99_ms"]},
                    ],
                    "depends_on": ["eval_config"],
                },
                {
                    "phase": 5,
                    "name": "report_archive",
                    "estimated_min": 5,
                    "outputs": [
                        "workspace/Allure/eval/selftest-20260516-000005/",
                        "workspace/执行日志/eval/reports/",
                        "workspace/执行日志/eval/captures/",
                    ],
                    "depends_on": ["pass_at_k", "stability_check", "latency_check"],
                },
            ],
            "quality_gates": {
                "pass_at_1_min": 0.70,
                "jaccard_at_5_min": 0.60,
                "top1_stability_min": 0.90,
                "latency_p95_ms_max": 3000,
                "latency_delta_pct_max": 20,
                "pii_leak": 0,
            },
            "outputs": {
                "eval_dir": "workspace/执行日志/eval/",
                "capture_dir": "workspace/执行日志/eval/captures/",
                "replay_dir": "workspace/执行日志/eval/replays/",
                "report_dir": "workspace/执行日志/eval/reports/",
                "allure_dir": "workspace/Allure/eval/selftest-20260516-000005/",
            },
            "risks": [
                "黄金测试集过小 (<20 条) 致 pass@k 过拟合",
                "prompt 顺序敏感致 stability 假阳性 (建议 shuffle 5 次取均值)",
                "非确定性模型 (temperature>0) top-1 随机波动 (建议 temperature=0 测 stability)",
                "latency 受网络抖动影响 (建议同 region 测 + 剔除 P99 外异常值)",
                "PII 漏检致原始 query 入 eval report (建议 scrub 后人工抽查 5%)",
            ],
            "confidence": "medium",
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "执行日志" / "eval_harness_plan.json"

    def summary(self, output: dict[str, Any]) -> str:
        phases = len(output.get("phases", []))
        target = output.get("eval_target", "?")
        cases = sum(
            len(p.get("cases", [])) if isinstance(p, dict) else 0
            for p in output.get("phases", [])
        )
        gates = output.get("quality_gates", {})
        return (
            f"LLM 评测编排 {phases} 阶段 / 目标={target} / "
            f"用例 {cases} / pass@1≥{gates.get('pass_at_1_min', '?')}"
        )
