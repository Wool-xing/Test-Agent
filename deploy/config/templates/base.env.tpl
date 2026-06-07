# Test-Agent {{TAGENT_VERSION}} · 由 `tagent init` 生成于 {{GENERATED_AT}}
# 配置:test_type={{TEST_TYPE}}  platform={{PLATFORM}}  llm={{LLM_PROVIDER}}  bug_tracker={{BUG_TRACKER}}
# 通知:{{NOTIFIER_LIST}}
#
# ⚠ 填占位 <your_*> 字段后才能跑;尚未填的字段对应功能自动跳过(不阻塞)

# ===== LLM =====
TAGENT_LLM_PROVIDER={{LLM_PROVIDER}}
TAGENT_LLM_PROVIDER_FALLBACK=ollama
{{LLM_ENV_BLOCK}}

# ===== 被测对象 =====
{{TEST_REQUIRED_ENV_BLOCK}}

# ===== 平台 extras =====
{{PLATFORM_EXTRAS_BLOCK}}

# ===== BugTracker(主宪章 §37,默认 zentao,可换) =====
{{BUG_TRACKER_ENV_BLOCK}}

# ===== 多端通知(主宪章 §36,任意 1 个生效即可) =====
{{NOTIFIER_ENV_BLOCK}}

# ===== Test-Agent 运行时(通常不需改) =====
TAGENT_OTEL_ENABLED=false
TAGENT_DB_URL={{DB_URL}}
TAGENT_MINIO_ENDPOINT=localhost:9000
TAGENT_MINIO_ACCESS_KEY={{MINIO_ACCESS_KEY}}
TAGENT_MINIO_SECRET_KEY={{MINIO_SECRET_KEY}}
