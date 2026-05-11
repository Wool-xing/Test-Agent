---
id: flaky-vs-reruns
category: 08-gates
level: 中级
name_zh: Flaky 与 Reruns 哲学
name_en: Flaky vs Reruns Philosophy
one_liner_zh: 冒烟不重试保留 flaky 信号;回归重试追快反馈
one_liner_en: No reruns at smoke (preserve flaky signal); reruns at regression (fast feedback)
authority:
  - "Google Testing Blog: Flaky Tests at Google and How We Mitigate Them"
  - "pytest-rerunfailures docs"
  - ISTQB Advanced Test Manager §6 Risk-based Testing
confidence: high
last_reviewed: 2026-05-12
reviewer: agent-curator
when_to_use: 任何 CI/CD 决定是否开 --reruns 时
common_pitfall:
  - "冒烟阶段开 reruns → 隐藏 flaky 缺陷"
  - "回归全开 reruns 但不归档 → 永远不发现 flaky 率"
  - "Flaky >30% 不 quarantine → 噪音吞噬有效用例"
example: |
  - smoke:`pytest -m smoke`(无 reruns)
  - regression:`pytest -m "p0 or p1" --reruns=2 --reruns-delay=5`
  - flaky 检测:`utils/flaky_detector.py` 离线扫 history,失败率 >30% 标 quarantine
related_to: [test-pyramid-2024, ci-quality-gate, mutation-testing]
---
