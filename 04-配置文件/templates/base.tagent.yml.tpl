# Test-Agent {{TAGENT_VERSION}} · 由 `tagent init` 生成于 {{GENERATED_AT}}
# 这是项目级配置(超出 .env 范围的运行时行为);可被 ~/.tagent/config.yml 用户级配置覆盖。

project:
  test_type: {{TEST_TYPE}}
  platform: {{PLATFORM}}

router:
  llm_provider: {{LLM_PROVIDER}}
  llm_provider_fallback: ollama

skills:
  recommended:
{{RECOMMENDED_SKILLS_LIST}}

bug_tracker:
  primary: {{BUG_TRACKER}}
  # 多 tracker 并存(主宪章 §37):写成 [zentao, github],按 Bug label 路由
  # extra: [github]

notifiers:
  enabled: {{NOTIFIER_LIST_YAML}}

quality_gates:
  smoke_pass_rate_min: 0.95
  regression_pass_rate_min: 0.90
  coverage_min: 0.80
  perf_p99_ms_max: 300

selftest:
  # 主宪章 §33 自检铁律
  pre_tag_required: true
  pass_threshold: 0.80
  strict_on_release: true

marketplace:
  enabled: false        # 默认关 · 主宪章 §30 safe-by-default
