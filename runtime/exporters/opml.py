"""OPML 2.0 exporter · 通用思维导图交换格式.

支持工具:MindManager / Word 大纲 / Workflowy / OmniOutliner /
任何 RSS 阅读器 / Mindly 等.
XML 标准,无依赖.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement
from xml.sax.saxutils import escape

from runtime.exporters.base import Exporter, TestCaseNode, TestCaseTree, register


def _node_to_outline(parent: Element, node: TestCaseNode) -> None:
    attrs = {"text": escape(node.title)}
    if node.priority:
        attrs["_priority"] = node.priority
    if node.kind:
        attrs["_kind"] = node.kind
    if node.tags:
        attrs["_tags"] = ",".join(node.tags)
    # 摘要放 _note(用户在工具中能看到注解)
    note_lines: list[str] = []
    if node.preconditions:
        note_lines.append("前置:" + " | ".join(node.preconditions))
    if node.expected:
        note_lines.append("预期:" + " | ".join(node.expected))
    if node.notes:
        note_lines.append("备注:" + node.notes)
    if note_lines:
        attrs["_note"] = "\n".join(note_lines)

    outline = SubElement(parent, "outline", attrs)
    for child in node.children:
        _node_to_outline(outline, child)


@register("opml")
class OPMLExporter(Exporter):
    extension = ".opml"

    def export(self, tree: TestCaseTree, target: Path) -> Path:
        target = target.with_suffix(".opml") if target.suffix != ".opml" else target
        target.parent.mkdir(parents=True, exist_ok=True)

        opml = Element("opml", version="2.0")
        head = SubElement(opml, "head")
        SubElement(head, "title").text = tree.project_name
        SubElement(head, "dateCreated").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        SubElement(head, "ownerName").text = tree.author

        body = SubElement(opml, "body")
        _node_to_outline(body, tree.root)

        tree_xml = ElementTree(opml)
        tree_xml.write(target, encoding="utf-8", xml_declaration=True)
        return target
