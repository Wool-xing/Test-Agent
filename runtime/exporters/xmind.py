"""XMind .xmind exporter · 新版格式(content.json 驱动).

XMind 8+ / XMind ZEN / XMind 2020+ 全部用此格式.
ZIP 容器:content.json + metadata.json + manifest.json.
无需第三方 lib(用 zipfile + json 标准库).
"""

from __future__ import annotations

import json
import uuid
import zipfile
from pathlib import Path

from runtime.exporters.base import Exporter, TestCaseNode, TestCaseTree, register


def _new_id() -> str:
    return uuid.uuid4().hex


def _node_to_topic(node: TestCaseNode) -> dict:
    """Convert TestCaseNode → XMind topic JSON."""
    topic = {
        "id": node.id or _new_id(),
        "title": node.title,
    }
    # Markers(优先级 → 内置 marker:priority-1..5)
    markers: list[dict] = []
    if node.priority:
        pri_num = int(node.priority[1]) + 1  # P0→1, P3→4
        markers.append({"markerId": f"priority-{pri_num}"})
    if node.kind == "case":
        markers.append({"markerId": "task-start"})
    if markers:
        topic["markers"] = markers

    # Notes(前置 + 预期 + 备注)
    notes_lines: list[str] = []
    if node.preconditions:
        notes_lines.append("【前置】\n" + "\n".join(f"- {p}" for p in node.preconditions))
    if node.expected:
        notes_lines.append("【预期结果】\n" + "\n".join(f"- {e}" for e in node.expected))
    if node.notes:
        notes_lines.append("【备注】\n" + node.notes)
    if node.tags:
        notes_lines.append("【标签】" + ", ".join(node.tags))
    if notes_lines:
        topic["notes"] = {"plain": {"content": "\n\n".join(notes_lines)}}

    # Children
    if node.children:
        topic["children"] = {
            "attached": [_node_to_topic(c) for c in node.children]
        }
    return topic


def _tree_to_content_json(tree: TestCaseTree) -> list[dict]:
    return [{
        "id": _new_id(),
        "class": "sheet",
        "title": tree.project_name,
        "rootTopic": _node_to_topic(tree.root),
    }]


def _manifest() -> dict:
    return {
        "file-entries": {
            "content.json": {},
            "metadata.json": {},
            "manifest.json": {},
        }
    }


def _metadata(tree: TestCaseTree) -> dict:
    return {
        "creator": {"name": tree.author, "version": tree.version},
        "dataStructureVersion": "2",
    }


@register("xmind")
class XMindExporter(Exporter):
    extension = ".xmind"

    def export(self, tree: TestCaseTree, target: Path) -> Path:
        target = target.with_suffix(".xmind") if target.suffix != ".xmind" else target
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("content.json", json.dumps(_tree_to_content_json(tree), ensure_ascii=False, indent=2))
            zf.writestr("metadata.json", json.dumps(_metadata(tree), ensure_ascii=False, indent=2))
            zf.writestr("manifest.json", json.dumps(_manifest(), ensure_ascii=False, indent=2))
        return target
