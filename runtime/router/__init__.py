"""AI router: input artifact -> expert+skill DAG.

Reads frontmatter of agents/*.md and skills/*.md via registry,
asks LLM (LiteLLM multi-provider + Ollama fallback) to produce a DAG.
"""
