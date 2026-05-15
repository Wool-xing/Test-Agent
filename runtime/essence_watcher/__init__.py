"""Essence watcher · 自动追踪 upstream reference repo 更新.

跑时:
  1. 解析 upstream INDEX 提取 repo url
  2. gh API 查最新 commit hash + 与上次记录 diff
  3. 若有新 commit → 拉 README + 关键 files
  4. LLM 萃取 delta(用 aux_client,主宪章 §22)
  5. 写 upstream update 文件 标 confidence: llm-draft-unreviewed
  6. 应用 policy 决定是否提议入 Test-Agent

接入 scheduler(主宪章 §22 §24 safe-by-default):
  - tagent.yml essence_watcher.enabled: true 才允许跑
  - 默认每周一次
"""
