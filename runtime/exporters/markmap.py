"""Markmap Markdown 嵌入式思维导图导出器.

Markmap = Markdown headings + nested lists → 可视化思维导图.
Renderers:markmap.js / VSCode 插件 / `markmap-cli` CLI / GitHub README 渲染.
零依赖(只 Markdown 文本).
"""

from __future__ import annotations

from pathlib import Path

from runtime.exporters.base import Exporter, TestCaseNode, TestCaseTree, register


def _node_to_md(node: TestCaseNode, depth: int = 1) -> list[str]:
    """Render node as Markdown (heading for depth ≤ 2,nested list for deeper)."""
    title = node.title
    if node.priority:
        title = f"**{node.priority}** · {title}"
    if node.kind == "case":
        title = f"🧪 {title}"

    lines: list[str] = []
    if depth <= 2:
        # heading
        lines.append(f"{'#' * (depth + 1)} {title}")
    else:
        # nested list bullet
        indent = "  " * (depth - 3)
        lines.append(f"{indent}- {title}")

    # Attach details as sub-bullets
    detail_indent = "  " * max(0, depth - 2)
    for p in node.preconditions:
        lines.append(f"{detail_indent}  - 前置:{p}")
    for e in node.expected:
        lines.append(f"{detail_indent}  - 预期:{e}")
    if node.notes:
        lines.append(f"{detail_indent}  - 备注:{node.notes}")
    if node.tags:
        lines.append(f"{detail_indent}  - 标签:{', '.join(node.tags)}")

    # Recurse
    for child in node.children:
        lines.extend(_node_to_md(child, depth + 1))
    return lines


@register("markmap")
class MarkmapExporter(Exporter):
    extension = ".md"

    def export(self, tree: TestCaseTree, target: Path) -> Path:
        target = target.with_suffix(".md") if target.suffix != ".md" else target
        target.parent.mkdir(parents=True, exist_ok=True)
        frontmatter = [
            "---",
            "markmap:",
            "  colorFreezeLevel: 2",
            "  initialExpandLevel: 3",
            "  duration: 500",
            f"title: {tree.project_name}",
            f"author: {tree.author}",
            f"version: {tree.version}",
            "---",
            "",
            f"# {tree.project_name}",
            "",
        ]
        body = _node_to_md(tree.root, depth=1)
        target.write_text("\n".join(frontmatter + body), encoding="utf-8")
        return target
