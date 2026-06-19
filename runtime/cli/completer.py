"""Tab completion for interactive REPL — slash commands + paths + agent/skill names.

Provides slash command completion, path completion, agent/skill name completion,
and context-aware completion for !model provider names.
"""

from __future__ import annotations

import logging

from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.document import Document

from runtime.cli.slash_commands import COMMAND_REGISTRY, _PROVIDERS

logger = logging.getLogger(__name__)

# Built-in REPL commands not in the global registry
_BUILTINS = [
    ("help", "Show help"),
    ("status", "Session stats + model info"),
    ("session", "Alias for !status"),
    ("model", "Switch LLM provider"),
    ("tools", "List agents + skills"),
    ("memory", "Show MEMORY.md contents"),
    ("remember", "Save fact to persistent memory"),
    ("forget", "Remove facts from memory"),
    ("cost", "Token usage and cost estimate"),
    ("sessions", "List saved sessions"),
    ("export", "Export conversation to markdown"),
    ("context", "Show conversation history"),
    ("clear", "Reset conversation memory"),
    ("compact", "Summarize and compress context"),
    ("quit", "Save and exit"),
    ("exit", "Alias for /quit"),
    ("usage", "Alias for /cost"),
    ("mcp", "List MCP tools across all servers"),
    ("mcp-call", "Call an MCP tool"),
    ("cron", "Manage scheduled tasks"),
    ("cron-health", "Schedule hourly health check"),
    ("model-router", "Show model auto-routing config"),
    ("ml", "Enter multi-line input mode"),
    ("multiline", "Enter multi-line input mode"),
    ("search", "Full-text search conversation history"),
    ("skill-score", "Score skills based on execution history"),
    ("speak", "Read test results aloud"),
    ("plugins", "List loaded plugins"),
]



class SlashCompleter(Completer):
    """Complete !commands, provider names, file paths, and agent/skill names."""

    def __init__(self):
        self._path_completer = PathCompleter(expanduser=True)
        self._catalog_names: list[tuple[str, str]] | None = None

    def _get_catalog_names(self) -> list[tuple[str, str]]:
        """Lazy-load agent/skill names from registry. Cached for session."""
        if self._catalog_names is None:
            try:
                from runtime.registry.registry import get_catalog
                cat = get_catalog()
                names = []
                for e in list(cat.experts.values()) + list(cat.skills.values()):
                    kind = "[agent]" if e.kind == "expert" else "[skill]"
                    names.append((e.name, f"{kind} {e.description[:50]}"))
                self._catalog_names = names
            except Exception:
                logger.warning("Failed to load catalog names for completer", exc_info=True)
                self._catalog_names = []
        return self._catalog_names

    def get_completions(self, document: Document, complete_event):
        text = document.text_before_cursor

        # After /, complete command names or context-aware args
        if text.startswith("!"):
            word = text.lstrip("!")

            # !model <provider> — complete provider names
            if word.startswith("model "):
                provider_part = word.split(" ", 1)[1]
                # If there's a second arg (model name), fall through to no completion
                if " " in provider_part:
                    return
                for p in _PROVIDERS:
                    if p.startswith(provider_part):
                        yield Completion(
                            p,
                            start_position=-len(provider_part),
                            display_meta="provider",
                        )
                return

            # Any command with args after space → path completion
            if " " in word:
                path_part = word.split(" ", 1)[1]
                path_doc = Document(path_part, len(path_part))
                yield from self._path_completer.get_completions(path_doc, complete_event)
                return

            # Complete command name (dedupe: COMMAND_REGISTRY names shadow _BUILTINS)
            seen = set()
            for c in COMMAND_REGISTRY:
                if c.name.startswith(word):
                    yield Completion(c.name, start_position=-len(word), display_meta=c.description)
                    seen.add(c.name)
            for name, desc in _BUILTINS:
                if name not in seen and name.startswith(word):
                    yield Completion(name, start_position=-len(word), display_meta=desc)
            return

        # Bare text: complete agent/skill names (min 2 chars to avoid noise)
        if len(text) >= 2:
            for name, desc in self._get_catalog_names():
                if name.startswith(text):
                    yield Completion(
                        name,
                        start_position=-len(text),
                        display_meta=desc,
                    )
