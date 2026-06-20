# Test-Agent {{TAGENT_VERSION}} · 由 `tagent init` 生成于 {{GENERATED_AT}}
# 配置: test_type={{TEST_TYPE}}  platform={{PLATFORM}}  llm={{LLM_PROVIDER}}  bug_tracker={{BUG_TRACKER}}
# 通知: {{NOTIFIER_LIST}}
# ⚠ 填 <your_*> 占位字段后才能跑；未填的字段对应功能自动跳过。

# ════ LLM ════
TAGENT_LLM_PROVIDER={{LLM_PROVIDER}}
TAGENT_LLM_API_KEY=<your_api_key_here>
# TAGENT_LLM_API_BASE=          # 中转站/代理/本地端点
# TAGENT_LLM_MODEL=             # 覆盖默认模型
# TAGENT_LLM_PROVIDER_FALLBACK=ollama
# TAGENT_EMBED_PROVIDER={{LLM_PROVIDER}}
{{LLM_ENV_BLOCK}}

# ════ 被测对象 ════
{{TEST_REQUIRED_ENV_BLOCK}}

# ════ 平台 extras ════
{{PLATFORM_EXTRAS_BLOCK}}

# ════ BugTracker ════
{{BUG_TRACKER_ENV_BLOCK}}

# ════ 通知 ════
{{NOTIFIER_ENV_BLOCK}}

# ════ Runtime ════
TAGENT_OTEL_ENABLED=false
TAGENT_DB_URL={{DB_URL}}
TAGENT_MINIO_ENDPOINT=localhost:9000
TAGENT_MINIO_ACCESS_KEY={{MINIO_ACCESS_KEY}}
TAGENT_MINIO_SECRET_KEY={{MINIO_SECRET_KEY}}
