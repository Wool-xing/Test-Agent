"""Healthcheck · L1 frontmatter lint + L3 LLM smoke(V1.10.0 · 主宪章 §33).

L1(本模块,无 LLM):agent/skill frontmatter 必填字段 + 注册表存在性
L2(CI mock):workflow `ci.yml` selftest job
L3(本模块 + CLI):`tagent doctor --agents` + `tagent selftest --e2e`
L4(weekly CI cron):`.github/workflows/selftest-weekly.yml`
"""
