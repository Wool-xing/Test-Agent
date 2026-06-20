"""CC-style full-screen TUI — Application + transcript + pinned input + status bar.

Layout (vertical, top→bottom):
  1. Transcript viewport (fills remaining space, scrollable)
  2. Separator line (dim)
  3. Input line with › prompt + right-aligned model
  4. Separator line (dim)
  5. Status bar (3-4 lines: model/project/health, context, config, tips)
"""

from __future__ import annotations

import re
from typing import Callable

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText

_RE_HTML = re.compile(r'<[^>]+>')

STYLE = Style.from_dict({
    "prompt": "bold cyan",
    "separator": "#888888",
    "bottom-toolbar": "bg:#1a1a2e fg:#a0a0c0",
    "transcript": "",
})


class CCTui:
    """Full-screen TUI matching CC layout density."""

    def __init__(
        self,
        on_input: Callable[[str], None],
        status_bar: Callable[[], str],
        model_display: Callable[[], str],
        completer=None,
        history=None,
    ):
        self._on_input = on_input
        self._status_bar = status_bar
        self._model_display = model_display

        # Transcript — all output goes here
        self._transcript: list[str] = []

        # Input buffer
        self._input_buf = Buffer(
            multiline=False,
            history=history,
            completer=completer,
            accept_handler=self._accept,
        )

        # Key bindings
        kb = KeyBindings()

        @kb.add("c-d")
        def _exit(event):
            event.app.exit()

        @kb.add("c-l")
        def _redraw(event):
            event.app.renderer.clear()
            event.app.invalidate()

        @kb.add("escape", "enter")
        def _newline(event):
            event.app.current_buffer.insert_text("\n")

        layout = Layout(
            HSplit([
                # 1. Transcript (scrollable)
                Window(
                    content=FormattedTextControl(
                        text=self._render_transcript,
                        focusable=False,
                    ),
                    wrap_lines=True,
                    always_hide_cursor=True,
                ),
                # 2. Separator
                Window(height=1, char="─", style="class:separator"),
                # 3. Input with prompt
                Window(
                    content=BufferControl(buffer=self._input_buf),
                    height=1,
                    get_line_prefix=lambda n, w: [("class:prompt", "❯ ")],
                ),
                # 4. Separator
                Window(height=1, char="─", style="class:separator"),
                # 5. Status bar
                Window(
                    height=5,
                    content=FormattedTextControl(
                        text=self._render_status,
                        focusable=False,
                    ),
                    style="class:bottom-toolbar",
                ),
            ])
        )

        self._app = Application(
            layout=layout,
            key_bindings=kb,
            style=STYLE,
            full_screen=True,
            mouse_support=True,
        )

    # ── Callbacks ──

    def _render_transcript(self) -> FormattedText:
        if not self._transcript:
            return FormattedText([("class:transcript", "")])
        text = "\n".join(self._transcript[-500:])
        return FormattedText([("class:transcript", text)])

    def _render_status(self) -> FormattedText:
        raw = self._status_bar()
        clean = _RE_HTML.sub('', raw)
        return FormattedText([("class:bottom-toolbar", clean)])

    def _accept(self, buf: Buffer) -> bool:
        text = buf.text.strip()
        buf.reset()
        if text:
            self.append_output(f"❯ {text}")
            self._on_input(text)
        return True

    # ── Public API ──

    def append_output(self, text: str) -> None:
        """Append Rich markup text to transcript (renders as plain text)."""
        clean = _RE_HTML.sub('', text)
        for line in clean.split("\n"):
            self._transcript.append(line)
        if len(self._transcript) > 5000:
            self._transcript = self._transcript[-3000:]
        self._app.invalidate()

    def run(self) -> None:
        self._app.run()

    def exit(self) -> None:
        self._app.exit()
