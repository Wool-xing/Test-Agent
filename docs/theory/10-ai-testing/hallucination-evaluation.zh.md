---
id: hallucination-evaluation
category: 10-ai-testing
level: 中级
name_zh: LLM 幻觉评估
name_en: LLM Hallucination Evaluation
one_liner_zh: LLM 输出 vs 事实/源文档的事实一致性度量
one_liner_en: Measure factual consistency of LLM outputs vs ground truth/source
authority:

  - "OWASP LLM Top 10:2025 LLM06 Sensitive Info Disclosure + LLM09 Misinformation"
  - "Anthropic Research: Constitutional AI / Honesty papers"
  - "DeepEval framework https://github.com/confident-ai/deepeval"
  - "Hugging Face Evaluate https://huggingface.co/docs/evaluate"
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
when_to_use: 任何 LLM 应用上线前/迭代后;RAG 系统必测
common_pitfall:

  - "只看 BLEU/ROUGE → 不能测幻觉"
  - "无源文档 ground truth → 无法判定事实"
  - "不分类型(extrinsic 编造 vs intrinsic 矛盾)"
example: |
  指标:

  - Faithfulness:输出与源文档一致率(RAG 必)
  - Answer Relevancy:答案与问题相关性
  - Context Precision/Recall:检索质量
  - GEval(LLM-as-judge with rubric)
  工具:DeepEval / ragas / HF Evaluate / LangSmith
related_to: [prompt-injection, model-drift, rag-evaluation]
---
