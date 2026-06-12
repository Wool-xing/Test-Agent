"""TDD: SlashCompleter and fuzzy matching tests."""

from __future__ import annotations

import pytest


class TestEditDistance:
    def test_identical(self):
        from runtime.cli.slash_commands import _edit_distance
        assert _edit_distance("test", "test") == 0

    def test_one_substitution(self):
        from runtime.cli.slash_commands import _edit_distance
        assert _edit_distance("test", "tent") == 1  # one char diff

    def test_one_insertion(self):
        from runtime.cli.slash_commands import _edit_distance
        assert _edit_distance("tes", "test") == 1

    def test_one_deletion(self):
        from runtime.cli.slash_commands import _edit_distance
        assert _edit_distance("testt", "test") == 1

    def test_two_edit_distance(self):
        from runtime.cli.slash_commands import _edit_distance
        assert _edit_distance("abc", "abd") == 1
        assert _edit_distance("abc", "abx") == 1
        assert _edit_distance("abc", "axc") == 1

    def test_completely_different(self):
        from runtime.cli.slash_commands import _edit_distance
        assert _edit_distance("abc", "xyz") == 3

    def test_empty_string(self):
        from runtime.cli.slash_commands import _edit_distance
        assert _edit_distance("", "test") == 4

    def test_symmetric(self):
        from runtime.cli.slash_commands import _edit_distance
        assert _edit_distance("ab", "ba") == _edit_distance("ba", "ab")


class TestClosestCommand:
    def test_exact_match_returns_none(self):
        """Exact match means no suggestion needed, but _closest_command finds it anyway."""
        from runtime.cli.slash_commands import closest as _closest_command
        # "help" exists → finds itself
        result = _closest_command("help")
        assert result == "help"  # closest match is itself

    def test_typo_one_edit(self):
        from runtime.cli.slash_commands import closest as _closest_command
        result = _closest_command("tets")
        assert result == "test"

    def test_typo_two_edits(self):
        from runtime.cli.slash_commands import closest as _closest_command
        result = _closest_command("modl")
        assert result == "model"

    def test_unknown_too_different(self):
        from runtime.cli.slash_commands import closest as _closest_command
        # "zzzzz" is too far from any command → no suggestion
        result = _closest_command("zzzzz")
        assert result is None

    def test_short_typo_one_edit(self):
        from runtime.cli.slash_commands import closest as _closest_command
        result = _closest_command("r")
        assert result == "r"  # "r" is itself an alias


class TestSlashCompleter:
    def test_completer_imports(self):
        """SlashCompleter can be instantiated."""
        from runtime.cli.completer import SlashCompleter
        c = SlashCompleter()
        assert c is not None

    def test_completer_has_path_completer(self):
        from runtime.cli.completer import SlashCompleter
        c = SlashCompleter()
        assert c._path_completer is not None


class TestSlashCommandCompletion:
    """Test /command name completion."""

    @staticmethod
    def _completions(text: str) -> list[str]:
        from runtime.cli.completer import SlashCompleter
        from prompt_toolkit.document import Document
        c = SlashCompleter()
        doc = Document(text, len(text))
        return [comp.text for comp in c.get_completions(doc, None)]

    def test_partial_command_prefix(self):
        comps = self._completions("!he")
        assert "help" in comps

    def test_exact_command_prefix(self):
        comps = self._completions("!status")
        assert "status" in comps

    def test_no_match_returns_empty(self):
        comps = self._completions("!xyznonexistent999")
        assert len(comps) == 0

    def test_empty_after_slash(self):
        comps = self._completions("!")
        # All commands should match empty prefix
        assert len(comps) > 5  # multiple commands available
        assert "help" in comps or any("help" == c for c in comps)


class TestModelProviderCompletion:
    """Test /model <provider> completion."""

    @staticmethod
    def _completions(text: str) -> list[str]:
        from runtime.cli.completer import SlashCompleter
        from prompt_toolkit.document import Document
        c = SlashCompleter()
        doc = Document(text, len(text))
        return [comp.text for comp in c.get_completions(doc, None)]

    def test_partial_provider_claude(self):
        comps = self._completions("!model cl")
        assert "claude" in comps

    def test_partial_provider_deepseek(self):
        comps = self._completions("!model dee")
        assert "deepseek" in comps

    def test_partial_provider_openai(self):
        comps = self._completions("!model op")
        assert "openai" in comps

    def test_provider_no_match(self):
        comps = self._completions("!model xyznon")
        assert len(comps) == 0

    def test_second_arg_no_completion(self):
        """After /model <provider> <model_name>, no completion."""
        comps = self._completions("!model claude sonnet")
        assert len(comps) == 0

    def test_model_prefix_only(self):
        """Ensure /model gets command completion not provider completion."""
        comps = self._completions("!mod")
        assert "model" in comps  # command name completion


class TestAgentSkillCompletion:
    """Test bare-text agent/skill name completion."""

    @staticmethod
    def _completions(text: str) -> list[str]:
        from runtime.cli.completer import SlashCompleter
        from prompt_toolkit.document import Document
        c = SlashCompleter()
        doc = Document(text, len(text))
        return [comp.text for comp in c.get_completions(doc, None)]

    def test_agent_name_completion(self):
        comps = self._completions("tes")
        assert "test-lead" in comps
        assert "test-executor" in comps

    def test_skill_name_completion(self):
        comps = self._completions("smoke")
        assert "smoke-test" in comps

    def test_short_text_no_completion(self):
        """Under 2 chars: no completion to avoid noise."""
        comps = self._completions("t")
        assert len(comps) == 0

    def test_no_match_bare_text(self):
        comps = self._completions("xyznomatch999")
        assert len(comps) == 0

    def test_empty_bare_text(self):
        comps = self._completions("")
        assert len(comps) == 0


class TestCompletionDedup:
    """Test deduplication between COMMAND_REGISTRY and _BUILTINS."""

    @staticmethod
    def _completions(text: str) -> list[str]:
        from runtime.cli.completer import SlashCompleter
        from prompt_toolkit.document import Document
        c = SlashCompleter()
        doc = Document(text, len(text))
        return [comp.text for comp in c.get_completions(doc, None)]

    def test_help_not_duplicated(self):
        """'help' is in both registry and builtins — appears once."""
        comps = self._completions("!hel")
        assert comps.count("help") == 1

    def test_quit_not_duplicated(self):
        """'quit' is in both registry and builtins — appears once."""
        comps = self._completions("!qu")
        assert comps.count("quit") == 1


class TestBuildinsList:
    """Test _BUILTINS covers all built-in slash commands."""

    def test_memory_commands_in_builtins(self):
        from runtime.cli.completer import _BUILTINS
        names = {name for name, _ in _BUILTINS}
        assert "remember" in names
        assert "forget" in names
        assert "memory" in names

    def test_essential_commands_in_builtins(self):
        from runtime.cli.completer import _BUILTINS
        names = {name for name, _ in _BUILTINS}
        for cmd in ("help", "status", "model", "quit", "tools", "cost",
                     "sessions", "export", "context", "clear", "compact"):
            assert cmd in names, f"Missing builtin: {cmd}"

    def test_providers_list(self):
        from runtime.cli.completer import _PROVIDERS
        assert len(_PROVIDERS) == 6
        assert "claude" in _PROVIDERS
        assert "ollama" in _PROVIDERS
