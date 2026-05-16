# runtime/exporters 索引(V1.9.0)

> 用例多格式导出 · 用户自选 · 默认 Excel(已有)+ 3 新格式.

## 注册的 exporter

| 名 | 扩展 | 用途 | 工具兼容 |
|----|------|------|---------|
| `xmind` | `.xmind` | XMind 思维导图(P0) | XMind 8/Zen/2020+ / Mind+ / 大厂主流 |
| `markmap` | `.md` | Markmap Markdown 嵌入 | markmap.js / VSCode 插件 / GitHub README 直渲 |
| `opml` | `.opml` | OPML 通用大纲 | MindManager / Word / Workflowy / OmniOutliner |

(保留)Excel 4-Sheet → `utils/excel_generator.py`(已有)

## 中间表示(IR)

所有 exporter 共用 `TestCaseTree`(`base.py`):

```python
@dataclass
class TestCaseNode:
    title: str
    kind: "module" | "feature" | "case" | "step"
    priority: "P0" | "P1" | "P2" | "P3" | None
    preconditions: list[str]
    expected: list[str]
    notes: str
    tags: list[str]
    children: list[TestCaseNode]

@dataclass
class TestCaseTree:
    project_name: str
    root: TestCaseNode
    version: str
    author: str
```

`testcase-designer` 专家 / `/testcase-design` skill 产此 IR,再 dispatch 到具体 exporter.

## CLI(V1.9 加)

```bash
tagent export <plan.json> --format xmind --out workspace/测试用例/login.xmind
tagent export <plan.json> --format markmap --out workspace/测试用例/login.md
tagent export <plan.json> --format opml --out workspace/测试用例/login.opml
tagent export <plan.json> --format all --out-dir workspace/测试用例/
```

`<plan.json>` 是 TestCaseTree 的 JSON 序列化(testcase-designer 输出).

## 扩展点(P1 / P2 留位)

未来加(若用户需求):
- `freemind`(.mm 老牌开源)
- `plantuml`(文本驱动 mindmap)
- `mermaid-mindmap`(Markdown 嵌入,GitHub 渲染)

## 与主宪章关系

- §5 多格式 I/O(扩输出端 3 种思维导图格式)
- §27 简洁优先:**只加用户用得到的 3 格式**(P0+P1),P2 留位
