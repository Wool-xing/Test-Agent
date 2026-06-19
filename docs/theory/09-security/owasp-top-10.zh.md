---
id: owasp-top-10
category: 09-security
level: 基础
name_zh: OWASP Top 10 Web 应用风险
name_en: OWASP Top 10 Web Application Risks
one_liner_zh: 全球公认的 Web 安全最严重 10 类风险
one_liner_en: Globally recognized top 10 Web application security risks
authority:

  - "OWASP Top 10:2021 https://owasp.org/Top10/"
  - "OWASP API Security Top 10 2023"
  - "OWASP LLM Top 10 2025"
  - "NIST SP 800-115 信息安全测试技术指南"
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
when_to_use: 任何 Web/API/LLM 应用上线前安全自检
common_pitfall:

  - "只看 OWASP Top 10:2017 旧版"
  - "API 类项目未读 API Security Top 10(独立列表)"
  - "LLM 应用没看 LLM Top 10"
example: |
  Web Top 10:2021:
  A01 Broken Access Control / A02 Cryptographic Failures / A03 Injection /
  A04 Insecure Design / A05 Security Misconfig / A06 Vulnerable Components /
  A07 Auth Failures / A08 Software/Data Integrity / A09 Logging Failures / A10 SSRF
related_to: [sast-dast, fuzzing, pen-testing-red-team]
---
