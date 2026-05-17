# 配置模板库索引（V1.32.5）

> `tagent init` 交互向导从本目录读取模板 + matrix · 5 分钟生成 `.env` + `tagent.yml` + `STARTUP.md`。

## 速查表

| 文件 | 用途 | 何时改 |
|------|------|--------|
| `matrix.yaml` | **单源真理**:测试类型 / 平台 / LLM / BugTracker / 通知渠道枚举 + 各自 env 字段 | 加新选项(eg. 新 LLM provider)→ 改这一处即可 |
| `base.env.tpl` | `.env` 模板 + `{{var}}` 占位 | 改 .env 框架时 |
| `base.tagent.yml.tpl` | `tagent.yml` 模板(项目级配置) | 改运行时默认行为 |
| `STARTUP.md.tpl` | 给用户的启动指南模板(用户最先看的文件) | 改 onboard 文案 |

## 矩阵规模

8 测试类型 × 6 平台 × 5 LLM × 6 BugTracker × 6 通知 = **8640 种组合**,wizard 自动合成。

## 用法

```bash
tagent init                                 # 交互向导
tagent init --test-type web --platform linux --llm claude --bug-tracker zentao --notifier wechat,feishu --out workspace/
tagent init --preset minimal                # 一键最小可跑配置(web + linux + ollama + webhook + email)
```

## 加新选项

加 LLM provider 示例:
```yaml
# matrix.yaml 加节
llm_providers:
  moonshot:
    label: 月之暗面 Kimi
    env:
      MOONSHOT_API_KEY: "<your_moonshot_key>"
    model_hint: moonshot-v1-32k
```
向导自动列出,无需改 wizard 代码。

## 相关

- 主宪章 §5 多格式 I/O · §36 多端通知 canon · §37 BugTracker canon
- 上一级:[`../INDEX.md`](../INDEX.md)
- 实现:[`../../runtime/init/INDEX.md`](../../runtime/init/INDEX.md)
