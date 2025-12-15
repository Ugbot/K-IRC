"""Main K-IRC Textual application."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static


class MessageList(ListView):
    """Widget displaying chat messages."""

    def compose(self) -> ComposeResult:
        yield ListItem(Label("Welcome to K-IRC!"))
        yield ListItem(Label("Your actor mailbox is ready."))


class ChannelList(ListView):
    """Widget displaying available channels/contacts."""

    def compose(self) -> ComposeResult:
        yield ListItem(Label("#general"))
        yield ListItem(Label("#random"))


class StatusBar(Static):
    """Status bar showing connection state."""

    def compose(self) -> ComposeResult:
        yield Static("Disconnected", id="connection-status")


class ChatInput(Input):
    """Input widget for typing messages."""

    def __init__(self) -> None:
        super().__init__(placeholder="Type a message...")


class KircApp(App):
    """K-IRC: Kafka Relay Chat TUI Application."""

    TITLE = "K-IRC"
    SUB_TITLE = "Kafka Relay Chat"
    CSS_PATH = "kirc.tcss"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
        Binding("c", "connect", "Connect"),
        Binding("escape", "focus_input", "Focus Input", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-container"):
            with Vertical(id="sidebar"):
                yield Static("Channels", classes="section-title")
                yield ChannelList(id="channel-list")
                yield Static("Status", classes="section-title")
                yield StatusBar(id="status-bar")
            with Vertical(id="chat-area"):
                yield MessageList(id="message-list")
                yield ChatInput()
        yield Footer()

    def action_toggle_dark(self) -> None:
        """Toggle between dark and light theme."""
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"

    def action_connect(self) -> None:
        """Initiate connection to Kafka/PostgreSQL/Valkey."""
        status = self.query_one("#connection-status", Static)
        status.update("Connecting...")

    def action_focus_input(self) -> None:
        """Focus the chat input."""
        self.query_one(ChatInput).focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle message submission."""
        message = event.value.strip()
        if message:
            message_list = self.query_one("#message-list", MessageList)
            await message_list.append(ListItem(Label(f"> {message}")))
            event.input.clear()
            message_list.scroll_end()
