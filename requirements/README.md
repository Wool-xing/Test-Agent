# 按需安装 — 依赖分层

> Phase 2 已交付。六层分层文件已就绪。

## 六层结构

| 层 | 文件 | 触发条件 | 安装命令 |
|----|------|---------|---------|
| base | `requirements/base.txt` | 永远装 | `pip install -r requirements/base.txt` |
| mobile | `requirements/mobile.txt` | 选择 mobile | `pip install -r requirements/mobile.txt` |
| desktop | `requirements/desktop.txt` | 选择 desktop | `pip install -r requirements/desktop.txt` |
| visual | `requirements/visual.txt` | 选择 visual | `pip install -r requirements/visual.txt` |
| system | `requirements/system.txt` | 选择 IoT/音视频 | `pip install -r requirements/system.txt` |
| ai | `requirements/ai.txt` | 选择 AI/LLM | `pip install -r requirements/ai.txt` |
| perf | `requirements/perf.txt` | 选择性能 | `pip install -r requirements/perf.txt` |

每层文件通过 `-r base.txt` 引用基础依赖，避免重复定义。

## 设计原则

- 不强迫 mobile 用户装 desktop 工具
- 运行时缺依赖→反问用户是否补装，不静默自动装
- 补装走 `pip install --upgrade-strategy only-if-needed`
- `04-配置文件/requirements.txt` 保留作为全量安装参考
