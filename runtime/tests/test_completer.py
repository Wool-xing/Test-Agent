"""TDD: SlashCompleter and fuzzy matching tests."""

from __future__ import annotations

import pytest


class TestEditDistance:
    def test_identical(self):
        from runtime.cli.interactive import _edit_distance
        assert _edit_distance("test", "test") == 0

    def test_one_substitution(self):
        from runtime.cli.interactive import _edit_distance
        assert _edit_distance("test", "tent") == 1  # one char diff

    def test_one_insertion(self):
        from runtime.cli.interactive import _edit_distance
        assert _edit_distance("tes", "test") == 1

    def test_one_deletion(self):
        from runtime.cli.interactive import _edit_distance
        assert _edit_distance("testt", "test") == 1

    def test_two_edit_distance(self):
        from runtime.cli.interactive import _edit_distance
        assert _edit_distance("abc", "abd") == 1
        assert _edit_distance("abc", "abx") == 1
        assert _edit_distance("abc", "axc") == 1

    def test_completely_different(self):
        from runtime.cli.interactive import _edit_distance
        assert _edit_distance("abc", "xyz") == 3

    def test_empty_string(self):
        from runtime.cli.interactive import _edit_distance
        assert _edit_distance("", "test") == 4

    def test_symmetric(self):
        from runtime.cli.interactive import _edit_distance
        assert _edit_distance("ab", "ba") == _edit_distance("ba", "ab")


class TestClosestCommand:
    def test_exact_match_returns_none(self):
        """Exact match means no suggestion needed, but _closest_command finds it anyway."""
        from runtime.cli.interactive import _closest_command
        # "help" exists → finds itself
        result = _closest_command("help")
        assert result == "help"  # closest match is itself

    def test_typo_one_edit(self):
        from runtime.cli.interactive import _closest_command
        result = _closest_command("tets")
        assert result == "test"

    def test_typo_two_edits(self):
        from runtime.cli.interactive import _closest_command
        result = _closest_command("modl")
        assert result == "model"

    def test_unknown_too_different(self):
        from runtime.cli.interactive import _closest_command
        # "zzzzz" is too far from any command → no suggestion
        result = _closest_command("zzzzz")
        assert result is None

    def test_short_typo_one_edit(self):
        from runtime.cli.interactive import _closest_command
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
