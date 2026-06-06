"""TDD: Multi-line input — detection, fallback, code block handling."""

from __future__ import annotations

import pytest


class TestMultilineDetection:
    """Test _is_multiline_candidate()."""

    def test_empty_not_candidate(self):
        from runtime.cli.interactive import _is_multiline_candidate

        assert _is_multiline_candidate("") is False
        assert _is_multiline_candidate("   ") is False

    def test_code_block_markers(self):
        from runtime.cli.interactive import _is_multiline_candidate

        for marker in ['"""', "'''", '```']:
            assert _is_multiline_candidate(f"{marker}") is True
            assert _is_multiline_candidate(f" {marker}python") is True

    def test_embedded_newlines_paste(self):
        from runtime.cli.interactive import _is_multiline_candidate

        text = "line1\nline2\nline3"
        assert _is_multiline_candidate(text) is True

    def test_normal_text_not_candidate(self):
        from runtime.cli.interactive import _is_multiline_candidate

        assert _is_multiline_candidate("test the login page") is False
        assert _is_multiline_candidate("/help") is False


class TestFallbackMultiline:
    """Test _fallback_multiline with simulated input."""

    def test_fallback_single_line(self, monkeypatch):
        """Single line + empty line ends input."""
        inputs = iter(["first line", ""])

        def mock_input(_prompt=""):
            return next(inputs)

        monkeypatch.setattr("runtime.cli._shared.console.input", mock_input)

        from runtime.cli.interactive import _fallback_multiline

        result = _fallback_multiline()
        assert result == "first line"

    def test_fallback_code_block(self, monkeypatch):
        """Code block auto-continues until closing marker."""
        inputs = iter(["```python", "print('hello')", "```", ""])

        def mock_input(_prompt=""):
            return next(inputs)

        monkeypatch.setattr("runtime.cli._shared.console.input", mock_input)

        from runtime.cli.interactive import _fallback_multiline

        result = _fallback_multiline()
        assert "```python" in result
        assert "print('hello')" in result
        assert result.endswith("```")


class TestKeyBindings:
    """Test key bindings are registered."""

    def test_kb_has_bindings(self):
        from runtime.cli.interactive import _kb

        # KeyBindings object should exist and be iterable
        assert _kb is not None


class TestHelpIncludesMultiline:
    """Test /ml hint in help text."""

    def test_ml_command_documented(self):
        from runtime.cli.completer import _BUILTINS

        names = {n for n, _ in _BUILTINS}
        assert "ml" in names
        assert "multiline" in names
