# 文档样式约定(STYLE.md)

> Test-Agent 全仓 Markdown 文档统一约定 · V1.10.0 起强制 · pre-commit markdownlint 卡 MD001 / MD036。

---

## 1. 标题(`#` `##` `###`)

| 规则 | 说明 |
| ------ | ------ |
| 深度上限 | `###`(三级)。超过用列表或表格,不用 `####` |
| 递增不可跳 | `#` → `##` → `###`,**禁止**`#` → `###`(MD001 卡) |
| 一文一 `#` | 每个 `.md` 文件**仅一个**`#` 顶级标题(MD025) |
| 标题不加粗 | `## 标题` 不写成 `##**标题**`(双重强调多余) |

## 2. 加粗 `**bold**` 使用边界

**仅以下 3 种场景**:

| 场景 | 例 |
| ------ | ----- |
| 关键术语首次出现 | "采用**遍历性检验**:失败能否重来" |
| 表格表头(可选) | 表头单元格内的术语 |
| 警告 / 规则前缀 | "**规则**:敏感文件不入 repo" |

**禁止**:

- 整段加粗(用 blockquote `>` 代替)
- 把加粗当二级标题(用 `##` 而不是 `**章节名**`,MD036 卡)
- 整句加粗作强调(改用斜体 `*emphasis*` 或重构句式)

## 3. 列表

| 规则 | 说明 |
| ------ | ------ |
| 无序用 `-` | 不用 `*` `+`,统一 `-` |
| 缩进 2 空格 | 嵌套 `  -`,**禁止**tab |
| 行末无尾随空格 | pre-commit `trailing-whitespace` 卡 |

## 4. 表格

```markdown
| 列1 | 列2 |
| ----- | ----- |
| 值   | 值   |

```text

- 对齐:左对齐为默认,数字列可 `---:` 右对齐
- 表头加粗可省略(GitHub 默认渲染加粗)
- 单元格内换行用 `<br>`,不用真换行

## 5. 代码块

| 场景 | 用 |
| ------ | ----- |
| 多行代码 | 三反引号 + 语言 ```` ```python ```` (MD040 卡) |
| 单行命令 | ```` `tagent run` ```` (反引号) |
| 文件路径 | ```` `runtime/exporters/base.py` ```` |

## 6. 链接

- 相对路径:`[INDEX](INDEX.md)` 而非绝对
- 外链:`[GitHub](https://github.com/...)`,**禁止**bare URL(MD034)
- 锚点跳转用 `[文档样式](#文档样式)`,标题中文小写空格转 `-`

## 7. Emoji

- 装饰性 emoji 仅用于:
  - README 头部 hero 区(✓)
  - CHANGELOG 章节符号(`### Added` / `### Changed`)

-**禁止**:正文段落、表格单元格、标题里塞 emoji

## 8. 文件命名

| 类型 | 命名 |
| ------ | ------ |
| 文档 | `kebab-case.md`(如 `quick-start.md`) |
| 索引 | `INDEX.md`(纯大写) |
| 自动产出 | `<topic>_<YYYYMMDD>.md` |

## 9. 中英混排

- 中英之间加半角空格:`使用 Python 编写`(非 `使用Python编写`)
- 标点统一中文:句号 `。`、逗号 `,`、冒号 `:`(英文标点仅用于代码块内)
- 数字与中文之间加空格:`16 个 agent`

## 10. 例外

| 场景 | 例外 |
| ------ | ------ |
| 上游引入文件 | `skills/(darwin-skill\|karpathy-guidelines)/*` 沿用上游样式,不批改 |
| 自动生成文件 | `CHANGELOG.md` 由 Keep-a-Changelog 模板驱动 |
| 本地笔记 | 项目根 gitignored 文件不受本约束 |

---

## 强制 hook

`.pre-commit-config.yaml` 启用以下规则:

```yaml

- id: markdownlint
  args:

    - --rules MD001    # heading-increment
    - --rules MD025    # single-h1
    - --rules MD036    # no-emphasis-as-heading
    - --rules MD034    # no-bare-urls

```text

违反提交即拒绝。修法:`markdownlint-cli --fix <file.md>`。
