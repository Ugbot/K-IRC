from datetime import datetime
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Input, Label, ListItem, ListView, Static
from textual.reactive import reactive
import random

class ChatMessage(ListItem):
    """A widget to display a single chat message with metadata."""

    def __init__(self, sender: str, message: str, timestamp: str = None) -> None:
        super().__init__()
        self.sender = sender
        self.message = message
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="message-header"):
            yield Label(f"<{self.sender}>", classes="message-sender")
            yield Label(self.timestamp, classes="message-time")
        yield Label(self.message, classes="message-content")


class MessageList(ListView):
    """Widget displaying chat messages."""

    def compose(self) -> ComposeResult:
        # Initial boot messages
        yield ListItem(Label("[bold green]SYSTEM_BOOT_SEQUENCE_INITIATED...[/]"))
        yield ListItem(Label("[bold cyan]CONNECTING_TO_NEURAL_NET...[/]"))
        yield ListItem(Label("[bold magenta]ACTOR_MAILBOX_READY[/]"))

    async def add_message(self, user: str, message: str):
        await self.mount(ChatMessage(user, message))
        self.scroll_end()


class ChannelItem(ListItem):
    """A widget for a channel in the sidebar."""
    
    def __init__(self, name: str, is_active: bool = False) -> None:
        super().__init__()
        self.channel_name = name
        self.is_active = is_active

    def compose(self) -> ComposeResult:
        prefix = ">>" if self.is_active else "  "
        style = "bold cyan" if self.is_active else "dim cyan"
        yield Label(f"{prefix} #{self.channel_name}", classes=f"channel-name {style}")


class DMItem(ListItem):
    """A widget for a DM in the sidebar."""
    
    def __init__(self, username: str, status: str = "online") -> None:
        super().__init__()
        self.username = username
        self.status = status

    def compose(self) -> ComposeResult:
        status_color = "green" if self.status == "online" else "red"
        yield Label(f"● {self.username}", classes=f"dm-name {status_color}")


class NodeList(ListView):
    """Widget displaying available nodes (channels)."""

    def compose(self) -> ComposeResult:
        yield ChannelItem("NET_RUNNERS", is_active=True)
        yield ChannelItem("BLACK_ICE")
        yield ChannelItem("GHOST_IN_SHELL")


class DMList(ListView):
    """Widget displaying direct messages."""
    
    def compose(self) -> ComposeResult:
        yield DMItem("Morpheus", "online")
        yield DMItem("Trinity", "online")
        yield DMItem("Neo", "offline")


class SystemStatus(Static):
    """Status bar showing connection state and system stats."""

    def compose(self) -> ComposeResult:
        yield Static("[bold red]OFFLINE[/]", id="connection-status")
        yield Static("[dim]MEM: 64TB | CPU: 12%[/]", id="system-stats")
        yield Static("[dim]UPLINK: 0.0 Kbps[/]", id="uplink-stats")

    def on_mount(self) -> None:
        """Start the system monitoring simulation."""
        self.set_interval(1.0, self.update_stats)

    def update_stats(self) -> None:
        """Update fake system stats."""
        cpu = random.randint(5, 45)
        mem = random.randint(10, 80)
        uplink = random.uniform(0.1, 50.0)
        
        self.query_one("#system-stats", Static).update(f"[dim]MEM: {mem}TB | CPU: {cpu}%[/]")
        self.query_one("#uplink-stats", Static).update(f"[dim]UPLINK: {uplink:.1f} Kbps[/]")

    def set_status(self, status: str, color: str = "green"):
        self.query_one("#connection-status", Static).update(f"[bold {color}]{status}[/]")


class ChatInput(Input):
    """Input widget for typing messages."""

    def __init__(self) -> None:
        super().__init__(placeholder=">_ EXECUTE COMMAND OR TRANSMIT...")
