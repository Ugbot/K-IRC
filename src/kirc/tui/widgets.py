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
    
    status = reactive("offline")

    def __init__(self, username: str, status: str = "offline") -> None:
        super().__init__()
        self.username = username
        self.status = status

    def compose(self) -> ComposeResult:
        yield Label(f"● {self.username}", id=f"dm-{self.username}", classes="dm-name")

    def watch_status(self, new_status: str) -> None:
        """Update color based on status."""
        try:
            label = self.query_one(f"#dm-{self.username}", Label)
            label.remove_class("green", "red", "yellow")
            color = "green" if new_status == "online" else "red"
            if new_status == "away": color = "yellow"
            label.add_class(color)
        except:
            pass


class NodeList(ListView):
    """Widget displaying available nodes (channels)."""

    def compose(self) -> ComposeResult:
        # Start empty, populated by App
        return []

    async def update_channels(self, channels: list[str], active_channel: str = None):
        self.clear()
        for channel in channels:
            self.append(ChannelItem(channel, is_active=(channel == active_channel)))


class DMList(ListView):
    """Widget displaying direct messages."""
    
    def compose(self) -> ComposeResult:
        # Start empty, populated by App
        return []

    async def update_contacts(self, contacts: list[dict]):
        self.clear()
        for contact in contacts:
            self.append(DMItem(contact["username"], contact.get("status", "offline")))


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
        """Update real system stats."""
        import psutil
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        
        # Uplink is harder to measure without tracking throughput, 
        # so we'll keep it as a small random number or 0 for now.
        uplink = random.uniform(0.0, 5.0) 
        
        self.query_one("#system-stats", Static).update(f"[dim]MEM: {mem}% | CPU: {cpu}%[/]")
        self.query_one("#uplink-stats", Static).update(f"[dim]UPLINK: {uplink:.1f} Kbps[/]")

    def set_status(self, status: str, color: str = "green"):
        self.query_one("#connection-status", Static).update(f"[bold {color}]{status}[/]")


class ChatInput(Input):
    """Input widget for typing messages."""

    def __init__(self) -> None:
        super().__init__(placeholder=">_ EXECUTE COMMAND OR TRANSMIT...")


class TypingIndicator(Static):
    """Shows who is currently typing."""

    users = reactive(set())

    def __init__(self, **kwargs) -> None:
        super().__init__("", **kwargs)

    def watch_users(self, users: set[str]) -> None:
        if not users:
            self.update("")
        else:
            names = ", ".join(sorted(list(users)))
            suffix = "is typing..." if len(users) == 1 else "are typing..."
            self.update(f"[dim italic]{names} {suffix}[/]")
