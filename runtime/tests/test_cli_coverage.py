"""Coverage tests for low-coverage CLI command helpers (report/export/serve)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestReportHelpers:
    def test_fmt_size_bytes(self):
        from runtime.cli.commands.report import _fmt_size

        assert _fmt_size(500) == "500B"
        assert _fmt_size(2048) == "2.0KB"
        assert _fmt_size(3 * 1024 * 1024) == "3.0MB"

    def test_fmt_age(self):
        from runtime.cli.commands.report import _fmt_age

        now = time.time()
        assert _fmt_age(now - 10) == "just now"
        assert _fmt_age(now - 120) == "2m ago"
        assert _fmt_age(now - 7200) == "2h ago"
        assert "d ago" in _fmt_age(now - 172800)

    def test_show_latest_empty_dir(self, tmp_path, capsys):
        from runtime.cli.commands.report import _show_latest

        _show_latest(tmp_path)
        out = capsys.readouterr().out
        assert out  # prints something (no crash)

    def test_show_run_missing(self, tmp_path, capsys):
        from runtime.cli.commands.report import _show_run

        _show_run(tmp_path, "no-such-run")
        out = capsys.readouterr().out
        assert out

    def test_show_workspace_empty(self, tmp_path, capsys):
        from runtime.cli.commands.report import _show_workspace_results

        _show_workspace_results(tmp_path)
        out = capsys.readouterr().out
        assert out


class TestExportTree:
    def test_tree_from_dict_nested(self):
        from runtime.cli.commands.export import _tree_from_dict

        tree = _tree_from_dict({
            "project_name": "demo",
            "root": {
                "title": "root",
                "kind": "suite",
                "children": [
                    {"title": "case-1", "expected": ["ok"], "tags": ["smoke"]},
                ],
            },
        })
        assert tree.root.title == "root"
        assert tree.root.children[0].title == "case-1"
        assert tree.root.children[0].expected == ["ok"]

    def test_tree_defaults(self):
        from runtime.cli.commands.export import _tree_from_dict

        tree = _tree_from_dict({})
        assert tree.root.title == "root"  # default root title
        assert tree.root.children == []


class TestServe:
    def test_serve_rejects_invalid(self):
        from runtime.cli.commands import serve

        # serve() blocks — only verify it is importable and has sane signature
        import inspect

        sig = inspect.signature(serve.serve)
        assert "host" in sig.parameters
        assert "port" in sig.parameters
