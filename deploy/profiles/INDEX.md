# profiles/ 索引(V1.10.0)

> 行业合规 profile 配置 · 测试时按行业自动加载额外规则。

## 速查表

| 子目录 | 用途 | 何时启用 |
| -------- | ------ | ---------- |
| `compliance/` | 10 合规 profile YAML(GDPR/CCPA/PIPL/HIPAA/SOC2/PCI-DSS/IEC-61508/IEC-62304/ISO-26262/DO-178C) | 测试目标涉及该法规 / 行业 |

## 新手 5 分钟

1. 看 `compliance/INDEX.md` 选你行业匹配的 profile
2. 启用方式:`tagent run <target> --profile gdpr,hipaa`(多 profile 用逗号)
3. 加载的规则会注入到对应 agent 的检查清单中

## 高级用法

- 想加新 profile:复制现有 YAML 改字段(必填:`rule_id` / `severity` / `applies_to` / `check`)
- profile 之间冲突时:严格级别更高的胜出(`critical` > `high` > `medium`)
- 自定义企业内 profile 放 `~/.tagent/profiles/`(用户级,不入 repo)

## 相关

- 上一级:[`../README.md`](../../README.md)
- 主宪章 §17(九大簇维度边界)+ §25(渗透 & 安全)+ §26(车载 & 自动驾驶)
- 加载实现:`runtime/config/settings.py` profile 字段
