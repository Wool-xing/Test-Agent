"""Full-screen TUI — prompt_toolkit Application with transcript viewport + pinned input.

Replaces the PromptSession-based REPL with a Claude Code-style layout:
  - Scrollable transcript area (all output)
  - Separator
  - Input prompt with rprompt
  - Separator + status bar
"""

from __future__ import annotations

import re
from typing import Callable

_RE_MARKUP = re.compile(r'\[[^\]]*\]')  # strip Rich markup fallback

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText


class TranscriptTUI:
    """Full-screen TUI with scrollable output area + pinned input.

    Usage:
        tui = TranscriptTUI(
            input_handler=my_handler,
            status_bar=lambda: "status text",
            style=pt_style,
            history=file_history,
        )
        tui.append_output("Hello world")
        tui.run()
    """

    def __init__(
        self,
        input_handler: Callable[[str], None],
        status_bar: Callable[[], str],
        rprompt: Callable[[], str] | None = None,
        warning_line: Callable[[], str] | None = None,
        style: Style | None = None,
        history = None,
        completer = None,
    ):
        self.input_handler = input_handler
        self._status_bar = status_bar
        self._rprompt = rprompt or (lambda: "")
        self._warning = warning_line or (lambda: "")

        # Transcript
        self._lines: list[str] = []

        # Input — ghost text for tab completion
        self._input_buf = Buffer(
            multiline=False,
            history=history,
            completer=completer,
            complete_while_typing=True,
            accept_handler=self._on_accept,
        )

        # Key bindings
        self._kb = KeyBindings()

        @self._kb.add("c-d")
        def _exit(event):
            event.app.exit(result=None)

        @self._kb.add("c-l")
        def _redraw(event):
            event.app.renderer.clear()
            event.app.invalidate()

        @self._kb.add("escape", "enter")
        def _newline(event):
            event.app.current_buffer.insert_text("\n")

        # Layout
        self._app = Application(
            layout=self._build_layout(),
            key_bindings=self._kb,
            style=style or Style.from_dict({}),
            full_screen=True,
            mouse_support=True,
        )

    def _build_layout(self) -> Layout:
        def _transcript_text():
            text = "\n".join(self._lines[-200:]) if self._lines else " Welcome — type !help for commands"
            return FormattedText([("class:transcript", text)])

        def _status_text():
            import re as _re
            raw = self._status_bar()
            clean = _re.sub(r'<[^>]+>', '', raw)
            return FormattedText([("class:bottom-toolbar", clean)])

        def _warning_text():
            w = self._warning()
            if w:
                return FormattedText([("class:warning", f" ⚠ {w}")])
            return FormattedText([])

        children = [
            Window(
                content=FormattedTextControl(
                    text=_transcript_text,
                    focusable=False,
                ),
                wrap_lines=True,
                always_hide_cursor=True,
            ),
        ]

        # Warning banner (only shown when there are issues)
        w = self._warning()
        if w:
            children.append(
                Window(height=1, content=FormattedTextControl(
                    text=f" ⚠ {w}", focusable=False,
                ), style="class:warning")
            )

        children += [
            Window(height=1, char="─", style="class:separator"),
            Window(
                content=BufferControl(buffer=self._input_buf),
                height=1,
                get_line_prefix=lambda line_count, width: [
                    ("class:prompt", "❯ ")
                ],
            ),
            Window(height=5, content=FormattedTextControl(
                text=_status_text, focusable=False,
            ), style="class:bottom-toolbar"),
        ]

        return Layout(HSplit(children))

    def _on_accept(self, buf: Buffer) -> bool:
        text = buf.text.strip()
        if text:
            self.append_output(f"❯ {text}")
            self.input_handler(text)
        buf.reset()
        return True  # keep input open

    def append_output(self, text: str, style: str = "") -> None:
        """Append text to scrollable transcript. Converts Rich markup → ANSI."""
        # Convert Rich markup to ANSI text so it renders correctly in the transcript
        try:
            from rich.console import Console as RichConsole
            from rich.text import Text as RichText
            cap = RichConsole(record=True, width=120, color_system="standard")
            cap.print(RichText.from_markup(text) if text else "")
            rendered = cap.export_text(styles=False)
        except Exception:
            rendered = _RE_MARKUP.sub('', text) if text else ""

        for line in rendered.split("\n"):
            stripped = line.rstrip()
            if stripped or self._lines:
                self._lines.append(stripped)
        if len(self._lines) > 5000:
            self._lines = self._lines[-3000:]

    def run(self) -> None:
        self._app.run()

    def exit(self) -> None:
        self._app.exit()
