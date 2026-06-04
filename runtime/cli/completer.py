"""Tab completion for interactive REPL — slash commands + paths.

Uses prompt_toolkit (same as Hermes Agent CLI).
Provides: slash command completion, path completion, session command completion.
"""

from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.document import Document

from runtime.cli.slash_commands import COMMAND_REGISTRY

# Built-in REPL commands not in the global registry
_BUILTINS = [
    ("help", "Show help"),
    ("status", "Session stats + model info"),
    ("model", "Switch LLM provider"),
    ("context", "Show conversation history"),
    ("clear", "Reset conversation memory"),
    ("quit", "Save and exit"),
]


class SlashCompleter(Completer):
    """Complete /commands and file paths."""

    def __init__(self):
        self._path_completer = PathCompleter(expanduser=True)

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        # After /, complete command names
        if text.startswith("/"):
            word = text.lstrip("/")
            # If there's a space, we're in args — use path completion
            if " " in word:
                path_part = word.split(" ", 1)[1]
                path_doc = Document(path_part, len(path_part))
                yield from self._path_completer.get_completions(path_doc, complete_event)
                return

            # Complete command name
            all_cmds = [(c.name, c.description) for c in COMMAND_REGISTRY]
            all_cmds.extend(_BUILTINS)
            for name, desc in all_cmds:
                if name.startswith(word):
                    yield Completion(
                        name,
                        start_position=-len(word),
                        display_meta=desc,
                    )
            return

        # Bare text: no completion needed (natural language)
        return
