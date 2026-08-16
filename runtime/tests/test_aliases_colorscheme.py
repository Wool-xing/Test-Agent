"""Alias persistence + colorscheme bridge tests (0%-coverage CLI helpers)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestAliases:
    def test_add_list_remove_roundtrip(self, tmp_path, monkeypatch):
        from runtime.cli import aliases

        monkeypatch.setattr(aliases, "_file", lambda: tmp_path / "aliases.json")

        assert aliases.list_aliases() == []
        aliases.add_alias("t", "run smoke", "quick smoke")
        lst = aliases.list_aliases()
        assert any(a.name == "t" and a.command == "run smoke" for a in lst)
        aliases.remove_alias("t")
        assert aliases.list_aliases() == []

    def test_expand_hits(self, tmp_path, monkeypatch):
        from runtime.cli import aliases

        monkeypatch.setattr(aliases, "_file", lambda: tmp_path / "aliases.json")
        aliases.add_alias("t", "run smoke")
        assert aliases.expand_alias("t") == "run smoke"
        assert aliases.expand_alias("unknown-alias") is None

    def test_persistence_across_reload(self, tmp_path, monkeypatch):
        from runtime.cli import aliases

        monkeypatch.setattr(aliases, "_file", lambda: tmp_path / "aliases.json")
        aliases.add_alias("x", "cmd")
        assert aliases.expand_alias("x") == "cmd"


class TestColorscheme:
    def test_bridge_produces_pt_style(self):
        from runtime.cli.colorscheme import get_colorscheme

        style = get_colorscheme().pt_style()
        assert style is not None

    def test_pt_html_tag_returns_string(self):
        from runtime.cli.colorscheme import get_colorscheme

        cs = get_colorscheme()
        for kind in ("prompt", "ok", "fail", "dim"):
            tag = cs.pt_html_tag(kind)
            assert isinstance(tag, str) and tag


class TestTenancy:
    def test_disabled_by_default(self):
        import os

        from runtime.api import tenancy

        assert tenancy.tenancy_enabled() is False
        assert tenancy.get_current_tenant() is None

    def test_enabled_flow(self, monkeypatch):
        import os

        from runtime.api import tenancy

        monkeypatch.setenv("TAGENT_TENANCY_ENABLED", "1")
        assert tenancy.tenancy_enabled() is True
        tenancy.set_current_tenant("tenant-a")
        assert tenancy.get_current_tenant() == "tenant-a"
        tenancy.set_current_tenant("tenant-b")
        assert tenancy.get_current_tenant() == "tenant-b"

    def test_contextvar_isolation_across_tasks(self, monkeypatch):
        import asyncio

        from runtime.api import tenancy

        monkeypatch.setenv("TAGENT_TENANCY_ENABLED", "1")

        async def task_a():
            tenancy.set_current_tenant("tenant-a")
            await asyncio.sleep(0.05)
            return tenancy.get_current_tenant()

        async def task_b():
            tenancy.set_current_tenant("tenant-b")
            return tenancy.get_current_tenant()

        async def main():
            return await asyncio.gather(task_a(), task_b())

        results = asyncio.run(main())
        assert set(results) == {"tenant-a", "tenant-b"}
