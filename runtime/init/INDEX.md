# runtime/init/ 索引(V1.12.0)

> `tagent init` 配置自动组装 · 5 分钟从 0 到可跑 · 主宪章 §1 一键部署。

## 模块

| 文件 | 用途 |
|------|------|
| `matrix.py` | 加载 `config/templates/matrix.yaml`(单源真理) |
| `wizard.py` | 交互向导 + `from_args()` 非交互 + `from_preset()` 预设 |
| `renderer.py` | 把 `InitAnswers` + matrix + 模板 → `.env` + `tagent.yml` + `STARTUP.md` |

## 流程

```
matrix.yaml ──┐
              ├──► wizard.run_wizard() ──► InitAnswers ──► renderer.render_all() ──► (.env, tagent.yml, STARTUP.md)
模板 *.tpl ───┘                          ▲
                                         │
                              CLI args / preset(可绕过向导)
```

## 用法

```bash
# 交互向导(推荐首次用户)
tagent init

# 非交互(CI / 脚本)
tagent init --test-type web --platform linux --llm claude --bug-tracker zentao --notifier wechat,feishu

# preset 5 种:minimal / saas-web / 国内-web / mobile-android / security-pentest
tagent init --preset minimal

# 覆盖已有
tagent init --overwrite
```

## 加新选项

不改 wizard / renderer 代码,改 matrix.yaml 即可:
- 新 LLM provider → `llm_providers:` 加节
- 新 BugTracker → `bug_trackers:` 加节(主宪章 §37 6 adapter 之外加)
- 新通知渠道 → `notifiers:` 加节(主宪章 §36 6 渠道之外加)
- 新测试类型 → `test_types:` 加节 + 同步 `agents/` 加平台 expert(如需)

## 矩阵规模

8 测试类型 × 6 平台 × 5 LLM × 6 BugTracker × 6 通知 = **8640 种组合**,可参数化。

## 相关

- 主宪章 §1(同步铁律)+ §5(多格式 I/O)+ §7(一键部署)+ §36(多端)+ §37(BugTracker)
- 模板:[`config/templates/`](../../config/templates/INDEX.md)
- 集成 CLI:`runtime/cli/main.py` `init` 子命令
