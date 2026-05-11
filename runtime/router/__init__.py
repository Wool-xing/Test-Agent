"""AI router: input artifact -> expert+skill DAG.

Reads frontmatter of 02-专家定义/*.md and 03-技能定义/*.md via registry,
asks LLM (LiteLLM multi-provider + Ollama fallback) to produce a DAG.
"""
