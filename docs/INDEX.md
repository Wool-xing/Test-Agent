# docs/ 索引(V1.10.0-alpha)

> 项目文档总入口 · 样式规范 / 教学理论 KB / 演示素材 / 用户调研 · 几分钟即可定位。

## 速查表

| 文件 / 子目录 | 用途 | 何时看 |
|--------------|------|--------|
| `STYLE.md` | 全仓 Markdown 样式约定(标题/加粗/列表/表格/代码块/链接/emoji/命名/中英混排) | 写文档前必看一次 |
| `SURVEY.md` | 12 题用户调研模板(NPS + skill 使用率) | 想发用户问卷时 |
| `theory/` | **教学层 KB 13 大类**(主宪章 §23 §31) · `01-tools` ~ `13-build-your-own` | learn mode 推荐路径 |
| `assets/` | 演示素材 · `demo.recipe.md`(30 秒 demo 录制脚本)+ `terminalizer-config.yml` | 录演示视频时 |

## 新手 5 分钟

1. 先读 `STYLE.md` 了解项目文档基本约定
2. 想知道项目教学层怎么用 → `theory/INDEX.md`
3. 想录 demo / GIF → `assets/demo.recipe.md`

## 高级用法

- 写新 skill 前对样式吃不准 → 跑 `markdownlint <file.md>` 一次,违规自动报
- 想扩 theory KB 新大类 → 见 `theory/_schema.yaml` 元数据规范
- 想发用户调研 → `SURVEY.md` 复制改字段即用

## 相关

- 上一级:[`../README.md`](../README.md)
- 主宪章 §23(教学层准则)+ §31(KB 扩 13 大类)
- 样式约束:`.pre-commit-config.yaml` markdownlint hook(MD001/MD036)
