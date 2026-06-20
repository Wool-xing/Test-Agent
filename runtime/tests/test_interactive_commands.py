"""Characterization tests: Interactive REPL built-in commands."""

from __future__ import annotations

import pytest


class TestSlashHelp:
    def test_help_function_imports(self):
        from runtime.cli.interactive import _print_help
        assert callable(_print_help)


class TestSlashStatus:
    def test_status_function_imports(self):
        from runtime.cli.commands.slash_handlers import _cmd_status
        assert callable(_cmd_status)


class TestSlashModel:
    def test_model_list(self):
        from runtime.cli.commands.slash_handlers import _cmd_model
        assert callable(_cmd_model)

    def test_model_unknown_provider(self):
        from runtime.cli.interactive import _PROVIDERS
        assert "claude" in _PROVIDERS
        assert "ollama" in _PROVIDERS

    def test_current_provider_default(self):
        from runtime.cli.interactive import _current_provider
        provider = _current_provider()
        assert isinstance(provider, str)
        assert len(provider) > 0

    def test_current_model_returns_string(self):
        from runtime.cli.interactive import _current_model
        model = _current_model()
        assert isinstance(model, str)
        assert len(model) > 0


class TestSlashCost:
    def test_cost_function_imports(self):
        from runtime.cli.commands.slash_handlers import _cmd_cost
        assert callable(_cmd_cost)

    def test_estimate_cost_returns_tuple(self):
        from runtime.cli.commands.slash_handlers import _estimate_cost; from runtime.cli.interactive import _get_memory
        mem = _get_memory()
        tokens, cost = _estimate_cost(mem)
        assert isinstance(tokens, int)
        assert isinstance(cost, float)

    def test_price_table_has_all_providers(self):
        from runtime.cli.commands.slash_handlers import _PRICE_PER_1K; from runtime.cli.interactive import _PROVIDERS
        for p in _PROVIDERS:
            assert p in _PRICE_PER_1K, f"Missing pricing for {p}"

    def test_cost_formats_currency(self):
        from runtime.cli.commands.slash_handlers import _estimate_cost; from runtime.cli.interactive import _get_memory
        mem = _get_memory()
        mem.add("user", "test")
        mem.add("assistant", "done")
        _, cost = _estimate_cost(mem)
        assert cost >= 0


class TestSlashClear:
    def test_clear_resets_memory(self):
        from runtime.cli.commands.slash_handlers import _cmd_clear; from runtime.cli.interactive import _get_memory
        mem = _get_memory()
        mem.add("user", "hello")
        _cmd_clear("")
        assert len(mem.messages) == 0


class TestSlashContext:
    def test_context_function_imports(self):
        from runtime.cli.commands.slash_handlers import _cmd_context
        assert callable(_cmd_context)


class TestSlashSessions:
    def test_sessions_function_imports(self):
        from runtime.cli.commands.slash_handlers import _cmd_sessions
        assert callable(_cmd_sessions)


class TestSlashExport:
    def test_export_function_imports(self):
        from runtime.cli.commands.slash_handlers import _cmd_export
        assert callable(_cmd_export)


class TestSlashCompact:
    def test_compact_function_imports(self):
        from runtime.cli.commands.slash_handlers import _cmd_compact
        assert callable(_cmd_compact)

    def test_compact_too_few_turns(self):
        from runtime.cli.commands.slash_handlers import _cmd_compact; from runtime.cli.interactive import _get_memory
        mem = _get_memory()
        mem.clear()
        _cmd_compact("")  # should not crash with 0 messages
        assert len(mem.messages) == 0  # nothing to compact


class TestSlashTools:
    def test_tools_function_imports(self):
        from runtime.cli.commands.slash_handlers import _cmd_tools
        assert callable(_cmd_tools)


class TestSlashDispatch:
    def test_handle_slash_imports(self):
        from runtime.cli.interactive import _handle_slash
        assert callable(_handle_slash)

    def test_builtin_map_has_all_keys(self):
        from runtime.cli.slash_commands import resolve
        expected = {"help", "h", "?", "quit", "q", "exit", "status",
                     "model", "tools", "cost", "usage", "sessions",
                     "export", "compact", "context", "clear",
                     "remember", "forget", "memory",
                     "mcp", "mcp-call", "cron", "cron-health", "model-router"}
        for key in expected:
            assert resolve(key) is not None, f"Missing command: {key}"

    def test_closest_command_returns_none_for_gibberish(self):
        from runtime.cli.slash_commands import closest as _closest_command
        result = _closest_command("xyzwq")
        assert result is None

    def test_edit_distance_edge_cases(self):
        from runtime.cli.slash_commands import _edit_distance
        assert _edit_distance("", "") == 0
        assert _edit_distance("a", "") == 1
        assert _edit_distance("", "a") == 1


class TestFuzzyMatching:
    def test_common_typos_corrected(self):
        from runtime.cli.slash_commands import closest as _closest_command
        # These should all find matches
        assert _closest_command("modl") == "model"
        assert _closest_command("tets") == "test"
        assert _closest_command("contxt") == "context"

    def test_very_different_no_match(self):
        from runtime.cli.slash_commands import closest as _closest_command
        assert _closest_command("zzzpq") is None


class TestCostEstimation:
    def test_empty_memory_minimal_tokens(self):
        from runtime.cli.commands.slash_handlers import _estimate_cost; from runtime.cli.interactive import _get_memory
        mem = _get_memory()
        mem.clear()
        tokens, cost = _estimate_cost(mem)
        assert tokens >= 0
        assert cost >= 0.0

    def test_cost_scales_with_messages(self):
        from runtime.cli.commands.slash_handlers import _estimate_cost; from runtime.cli.interactive import _get_memory
        mem = _get_memory()
        mem.clear()
        mem.add("user", "x" * 400)
        mem.add("assistant", "y" * 400)
        tokens, cost = _estimate_cost(mem)
        assert tokens >= 100
        assert cost >= 0.0  # may be 0 if provider=stub

    def test_ollama_pricing_is_zero(self):
        from runtime.cli.commands.slash_handlers import _PRICE_PER_1K
        in_p, out_p = _PRICE_PER_1K["ollama"]
        assert in_p == 0
        assert out_p == 0

    def test_claude_pricing_positive(self):
        from runtime.cli.commands.slash_handlers import _PRICE_PER_1K
        in_p, out_p = _PRICE_PER_1K["claude"]
        assert in_p > 0
        assert out_p > 0


class TestCompact:
    def test_compact_too_few_messages(self):
        from runtime.cli.commands.slash_handlers import _cmd_compact; from runtime.cli.interactive import _get_memory
        mem = _get_memory()
        mem.clear()
        mem.add("user", "a")
        mem.add("assistant", "b")
        _cmd_compact("")  # should not crash with 2 messages
        assert len(mem.messages) == 2  # not enough to compact

    def test_compact_on_six_messages(self):
        from runtime.cli.commands.slash_handlers import _cmd_compact, _get_memory
        mem = _get_memory()
        mem.clear()
        for i in range(6):
            mem.add("user" if i % 2 == 0 else "assistant", f"msg {i}")
        _cmd_compact("")
        assert len(mem.messages) < 6  # compacted


class TestSessions:
    def test_sessions_no_crash(self):
        from runtime.cli.commands.slash_handlers import _cmd_sessions
        result = _cmd_sessions("")  # should not crash even with no sessions
        assert result is None


class TestExport:
    def test_export_empty_memory(self):
        from runtime.cli.commands.slash_handlers import _cmd_export, _get_memory
        mem = _get_memory()
        mem.clear()
        result = _cmd_export("")  # should not crash
        assert result is None

    def test_export_with_messages(self):
        from runtime.cli.commands.slash_handlers import _cmd_export, _get_memory
        mem = _get_memory()
        mem.add("user", "hello")
        result = _cmd_export("")  # should create export file
        assert result is None


class TestMemoryCommands:
    def test_remember_no_args(self):
        from runtime.cli.commands.slash_handlers import _cmd_remember
        result = _cmd_remember("")  # should not crash
        assert result is None

    def test_remember_and_forget(self):
        from runtime.cli.commands.slash_handlers import _cmd_remember, _cmd_forget
        from runtime.cli.conversation import load_memory_md
        _cmd_remember("Test fact: project uses Python")
        mem = load_memory_md()
        assert "Test fact: project uses Python" in mem
        _cmd_forget("Test fact")
        mem = load_memory_md()
        assert "Test fact: project uses Python" not in mem

    def test_forget_no_args(self):
        from runtime.cli.commands.slash_handlers import _cmd_forget
        result = _cmd_forget("")  # should not crash
        assert result is None

    def test_forget_nonexistent(self):
        from runtime.cli.commands.slash_handlers import _cmd_forget
        result = _cmd_forget("xyznonexistent123")  # should not crash
        assert result is None

    def test_memory_display(self):
        from runtime.cli.commands.slash_handlers import _cmd_memory
        result = _cmd_memory("")  # should not crash even when empty
        assert result is None

    def test_memory_builtin_registered(self):
        from runtime.cli.slash_commands import resolve
        assert resolve("remember") is not None
        assert resolve("forget") is not None
        assert resolve("memory") is not None

    def test_banner_imports_and_runs(self):
        from runtime.cli.interactive import _print_banner
        result = _print_banner()  # should not crash (animated or plain)
        assert result is None

    def test_error_diagnosis_imports(self):
        from runtime.cli.interactive import _diagnose_error
        # Test with a generic exception
        hint = _diagnose_error(Exception("Connection refused"))
        assert hint is not None  # should match connection pattern
        assert "Cannot reach" in hint

    def test_error_diagnosis_unknown(self):
        from runtime.cli.interactive import _diagnose_error
        hint = _diagnose_error(Exception("some random error"))
        assert hint is None  # no specific advice

    def test_error_diagnosis_api_key(self):
        from runtime.cli.interactive import _diagnose_error
        hint = _diagnose_error(Exception("Invalid API key provided"))
        assert hint is not None
        assert "API key" in hint

    def test_error_diagnosis_module_not_found(self):
        hint = None
        try:
            import nonexistent_module_for_test_12345  # noqa: F401
        except Exception as e:
            from runtime.cli.interactive import _diagnose_error
            hint = _diagnose_error(e)
        assert hint is not None
        assert "Missing" in hint
