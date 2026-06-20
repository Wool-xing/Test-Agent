"""Permission confirmation dialog — TUI popup for user consent (§Sprint 2)."""

from textual.app import ComposeResult
from textual.containers import Center, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmDialog(ModalScreen[bool]):
    """Modal dialog for permission confirmation. Returns True/False."""

    CSS = """
    Center {
        width: 60;
        height: auto;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
    }
    Static.question {
        text-style: bold;
        color: $warning;
        padding: 1 0;
    }
    Static.detail {
        color: $text-muted;
        padding-bottom: 1;
    }
    Vertical.buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }
    """

    def __init__(self, operation: str, target: str, detail: str = ""):
        super().__init__()
        self.operation = operation
        self.target = target
        self.detail = detail

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical():
                yield Static(f"Allow '{self.operation}'?", classes="question")
                yield Static(f"Target: {self.target}", classes="detail")
                if self.detail:
                    yield Static(self.detail[:200])
                with Vertical(classes="buttons"):
                    yield Button("Allow (Y)", variant="primary", id="allow")
                    yield Button("Deny (N)", variant="error", id="deny")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "allow":
            self.dismiss(True)
        else:
            self.dismiss(False)


def tui_confirm(operation: str, target: str) -> bool:
    """Show Textual permission confirmation dialog. Call from async context."""
    import asyncio
    from textual.app import App

    app = App.get_running_app()
    if app is None:
        # Fallback to Rich console if no TUI running
        from rich.prompt import Confirm
        return Confirm.ask(f"Allow '{operation}' on '{target}'?", default=False)

    async def _show():
        dialog = ConfirmDialog(operation, target)
        return await app.push_screen(dialog)

    return asyncio.get_event_loop().run_until_complete(_show())
