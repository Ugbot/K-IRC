"""Main K-IRC Textual application."""

import asyncio
from pathlib import Path
import base64
from uuid import uuid4

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static, ListView

from kirc.config import load_settings
from kirc.kafka.client import KafkaClient
from kirc.kafka.messages import ChatMessage as KircChatMessage
from kirc.cache.client import CacheClient
from kirc.db.client import DatabaseClient
from kirc.crypto import (
    generate_symmetric_key,
    encrypt_symmetric,
    decrypt_symmetric,
    encrypt_message,
    decrypt_message,
    load_key_from_file
)
from kirc.tui.widgets import ChatInput, MessageList, NodeList, DMList, SystemStatus, ChannelItem
from kirc.tui.exchange import InviteGenScreen, InviteAcceptScreen, ShowIdentityScreen
from kirc.tui.wizard import WizardScreen
from kirc.tui.settings import SettingsScreen


class KircApp(App):
    """K-IRC: Kafka Relay Chat TUI Application."""

    TITLE = "K-IRC v0.9.0 [BETA]"
    SUB_TITLE = "NEURAL_LINK_ESTABLISHED"
    CSS_PATH = "kirc.tcss"

    BINDINGS = [
        Binding("q", "quit", "ABORT"),
        Binding("d", "toggle_dark", "TOGGLE_VISUALS"),
        Binding("c", "connect", "INIT_LINK"),
        Binding("i", "invite_user", "INVITE_PEER"),
        Binding("j", "join_network", "JOIN_NET"),
        Binding("w", "wizard", "SETUP_WIZARD"),
        Binding("s", "settings", "Settings"),
        Binding("r", "rotate_keys", "Rotate Keys"),
        Binding("i", "show_identity", "Identity"),
        Binding("escape", "focus_input", "FOCUS_INPUT", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.kafka_client: KafkaClient | None = None
        self.cache_client: CacheClient | None = None
        self.db_client: DatabaseClient | None = None
        self.settings = load_settings()
        self._kafka_task: asyncio.Task | None = None
        self._cache_task: asyncio.Task | None = None
        
        self.private_key: bytes | None = None
        self.channel_keys: dict[str, dict[str, bytes]] = {} # channel_name -> {key_id -> symmetric_key}
        self.active_key_ids: dict[str, str] = {} # channel_name -> active_key_id

    current_channel = reactive("NET_RUNNERS")

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="main-container"):
            with Vertical(id="sidebar"):
                yield Static("ACTIVE_NODES", classes="section-title")
                yield NodeList(id="channel-list")
                yield Static("DIRECT_LINKS", classes="section-title")
                yield DMList(id="dm-list")
                yield Static("SYSTEM_STATUS", classes="section-title")
                yield SystemStatus(id="status-bar")
            with Vertical(id="chat-area"):
                yield MessageList(id="message-list")
                yield ChatInput()
        yield Footer()

    async def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle sidebar selection."""
        if event.list_view.id == "channel-list":
            item = event.item
            if isinstance(item, ChannelItem):
                self.current_channel = item.channel_name
                self.notify(f"Switched to #{self.current_channel}")
                # TODO: Clear message list and load history for new channel
                # For now just visual feedback
                
    async def watch_current_channel(self, new_channel: str) -> None:
        """React to channel changes."""
        # Update UI to reflect active channel
        # This would involve updating the NodeList highlighting and fetching history
        pass

    async def action_connect(self) -> None:
        """Connect to Kafka and Redis."""
        status_bar = self.query_one("#status-bar", SystemStatus)
        status_bar.set_status("CONNECTING...", "yellow")
        self.notify("Attempting connection...")

        if self.kafka_client and self.kafka_client.is_connected:
            self.notify("Already connected.", severity="information")
            status_bar.set_status("ONLINE", "green")
            return

        try:
            # Load private key
            key_path = Path(self.settings.user_config.private_key_path)
            if not key_path.exists():
                self.notify(f"Private key not found at {key_path}", severity="error")
                status_bar.set_status("KEY_MISSING", "red")
                return
            self.private_key = load_key_from_file(key_path)
            self.notify("Private key loaded.")

            self.kafka_client = KafkaClient(
                bootstrap_servers=self.settings.kafka_config.bootstrap_servers,
                group_id=self.settings.user_config.username,
                username=self.settings.user_config.username,
                password=self.settings.user_config.password,
                on_message_callback=self.handle_incoming_message,
                on_rpc_callback=self.handle_rpc
            )
            await self.kafka_client.connect()
            self.notify("Kafka client connected.")

            self.cache_client = CacheClient(
                host=self.settings.redis_config.host,
                port=self.settings.redis_config.port,
                password=self.settings.redis_config.password,
                username=self.settings.redis_config.username,
                on_key_rotation_callback=self.handle_key_rotation,
                on_channel_event_callback=self.handle_channel_event
            )
            await self.cache_client.connect()
            self.notify("Cache client connected.")

            self.db_client = DatabaseClient(
                db_path=self.settings.database_config.path
            )
            await self.db_client.connect()
            self.notify("Database client connected.")

            # Start Kafka consumer in a background task
            self._kafka_task = asyncio.create_task(self.kafka_client.start_consuming())
            self._cache_task = asyncio.create_task(self.cache_client.start_listening())

            # Subscribe to personal inbox for direct messages and RPCs
            await self.kafka_client.subscribe_to_topic(f"inbox-{self.settings.user_config.username}")
            await self.kafka_client.subscribe_to_topic(f"rpc-in-{self.settings.user_config.username}")
            self.notify(f"Subscribed to personal inbox: inbox-{self.settings.user_config.username}")

            # Subscribe to active channels and fetch history
            channels = ["NET_RUNNERS", "BLACK_ICE", "GHOST_IN_SHELL"]
            for channel in channels:
                # Join the channel (add to members list)
                await self.cache_client.join_channel(channel)
                
                leader = await self.cache_client.get_channel_leader(channel)
                if leader:
                    # Subscribe to leader's output topic (convention: out-{leader})
                    await self.kafka_client.subscribe_to_topic(f"out-{leader}")
                    
                    # Subscribe to rotation signals
                    await self.cache_client.subscribe_rotation(channel)
                    
                    # Subscribe to channel events
                    await self.cache_client.subscribe_channel_events(channel)
                    
                    # Fetch history from leader
                    asyncio.create_task(self.fetch_channel_history(channel, leader))

            status_bar.set_status("ONLINE [SECURE]", "green")
            self.notify("Connected to Neural Net")
            
        except Exception as e:
            status_bar.set_status("CONNECTION_FAILED", "red")
            self.notify(f"Connection Error: {str(e)}", severity="error")

    async def handle_rpc(self, message) -> None:
        """Handle incoming RPC messages."""
        if message.type == "fetch_history":
            channel = message.payload.get("channel")
            limit = message.payload.get("limit", 50)
            
            if self.db_client and channel:
                messages = await self.db_client.get_messages(channel=channel, limit=limit)
                
                # Send response
                response = KircChatMessage(
                    type="history_data",
                    sender=self.settings.user_config.username,
                    recipient=message.sender,
                    correlation_id=message.correlation_id,
                    payload={
                        "messages": [m.model_dump(mode="json") for m in messages]
                    }
                )
                
                target_topic = f"rpc-in-{message.sender}"
                await self.kafka_client.send_rpc(response, topic=target_topic)
        
        elif message.type == "channel_key_update":
            if not self.private_key:
                self.notify("Received channel key but no private key loaded!", severity="error")
                return

            try:
                channel = message.payload.get("channel")
                encrypted_key_b64 = message.payload.get("key")
                key_id = message.payload.get("key_id")
                encrypted_key = base64.b64decode(encrypted_key_b64)
                
                # Decrypt with our private key
                symmetric_key = decrypt_message(self.private_key, encrypted_key)
                
                if channel not in self.channel_keys:
                    self.channel_keys[channel] = {}
                
                if key_id:
                    self.channel_keys[channel][key_id] = symmetric_key
                    self.notify(f"Updated encryption key for #{channel} (ID: {key_id})")
                else:
                    self.notify("Received key update without ID", severity="warning")
                
            except Exception as e:
                self.notify(f"Failed to decrypt channel key: {e}", severity="error")

    async def fetch_channel_history(self, channel: str, leader: str) -> None:
        """Fetch history from channel leader."""
        if not self.kafka_client:
            return
            
        try:
            request = KircChatMessage(
                type="fetch_history",
                sender=self.settings.user_config.username,
                recipient=leader,
                payload={"channel": channel, "limit": 20}
            )
            
            target_topic = f"rpc-in-{leader}"
            response = await self.kafka_client.request(request, topic=target_topic, timeout=5.0)
            
            if response.type == "history_data":
                messages_data = response.payload.get("messages", [])
                message_list = self.query_one("#message-list", MessageList)
                
                for msg_data in reversed(messages_data):
                    sender = msg_data.get("sender", "UNKNOWN")
                    content = msg_data.get("content", "")
                    # Note: History messages are likely already decrypted or we need to handle that.
                    # For now assuming history is stored plaintext in local DB, but over wire?
                    # If leader sends history, they should probably re-encrypt with the REQUESTER's public key?
                    # Or just send plaintext if the RPC channel is considered secure (it's not really).
                    # For this step, let's assume history is sent as-is.
                    await message_list.add_message(sender, content)
                    
                self.notify(f"Synced {len(messages_data)} messages from #{channel}")
                
        except asyncio.TimeoutError:
            self.notify(f"History fetch timed out for #{channel}", severity="warning")
        except Exception as e:
            self.notify(f"Failed to fetch history: {e}", severity="error")

    async def handle_incoming_message(self, message) -> None:
        """Handle incoming Kafka messages."""
        if message.type == "chat":
            content = message.payload.get("content", "")
            channel = message.payload.get("channel")
            key_id = message.payload.get("key_id")
            
            # Decrypt if we have a key for this channel
            if channel in self.channel_keys:
                try:
                    # Expecting base64 encoded encrypted content
                    encrypted_content = base64.b64decode(content)
                    
                    # Find correct key
                    key = None
                    if key_id and key_id in self.channel_keys[channel]:
                        key = self.channel_keys[channel][key_id]
                    elif self.channel_keys[channel]:
                        key = next(iter(self.channel_keys[channel].values()))
                    
                    if key:
                        content = decrypt_symmetric(key, encrypted_content)
                    else:
                        content = "[ENCRYPTED - MISSING KEY]"
                        
                except Exception:
                    content = "[ENCRYPTED_DATA_STREAM]"
            
            # Save to DB (decrypted)
            if self.db_client:
                message.payload["content"] = content
                await self.db_client.save_message(message)
                
            # Update UI if this message belongs to current channel
            if channel == self.current_channel:
                message_list = self.query_one("#message-list", MessageList)
                await message_list.add_message(message.sender, content)

            # LEADER LOGIC: Re-broadcast if we are the leader
            # We check if the message was sent TO us (inbox) and needs distribution
            # We don't re-broadcast our own outbound messages if we just sent them via send_message
            # But wait, send_message sends to Leader. If WE are leader, we send to ourselves?
            # Ideally, if we are leader, we should just broadcast directly.
            
            if self.cache_client:
                leader = await self.cache_client.get_channel_leader(channel)
                if leader == self.settings.user_config.username:
                    # We are the leader.
                    # If this message came from someone else, we must forward it to the channel topic.
                    # The channel topic is our `data-out` (or specific channel topic).
                    # Subscribers listen to `out-{leader}`.
                    
                    if message.sender != self.settings.user_config.username:
                        # Re-encrypt? It came in encrypted. We decrypted it to show it.
                        # We can just forward the original payload if we want to preserve the exact message.
                        # BUT, we might want to re-sign or validate.
                        # For efficiency, let's forward the original encrypted payload.
                        
                        # Construct broadcast message
                        # We keep the original sender in the payload or metadata?
                        # Usually relay keeps original sender but wraps it?
                        # Or we just re-send the exact same message object?
                        # If we re-send, the 'sender' field is still the original user.
                        # That's fine for the UI.
                        
                        # We need to ensure we send it to `data-out`
                        # The KafkaClient.send_message defaults to `data-out`.
                        
                        # We need to be careful not to create a loop if we subscribe to our own outbox.
                        # (We usually don't subscribe to our own outbox).
                        
                        await self.kafka_client.send_message(message)
                        # self.notify(f"Relayed message from {message.sender}")

    def action_focus_input(self) -> None:
        """Focus the chat input."""
        self.query_one(ChatInput).focus()
        
    def action_invite_user(self) -> None:
        """Open the invite generation screen."""
        self.push_screen(InviteGenScreen())
        
    def action_join_network(self) -> None:
        """Open the invite acceptance screen."""
        self.push_screen(InviteAcceptScreen())

    def action_wizard(self) -> None:
        """Open the setup wizard."""
        self.push_screen(WizardScreen())

    def action_settings(self) -> None:
        """Open the settings screen."""
        self.push_screen(SettingsScreen())

    def action_show_identity(self) -> None:
        """Open the identity display screen."""
        self.push_screen(ShowIdentityScreen())

    async def action_rotate_keys(self) -> None:
        """Rotate keys for the current channel (Leader only)."""
        if not self.kafka_client or not self.db_client:
            return
            
        channel = self.current_channel
        
        # Check if we are leader
        leader = await self.cache_client.get_channel_leader(channel)
        if leader != self.settings.user_config.username:
            self.notify("ACCESS DENIED: Only channel leader can rotate keys", severity="error")
            return
            
        # Generate new key
        new_key = generate_symmetric_key()
        key_id = str(uuid4()) # Unique ID for this key version
        
        # Store locally
        if channel not in self.channel_keys:
            self.channel_keys[channel] = {}
        self.channel_keys[channel][key_id] = new_key
        
        # Get channel members from Redis
        members = await self.cache_client.get_channel_members(channel)
        
        # Distribute to all members who are also contacts (need public key)
        count = 0
        for member_username in members:
            # Skip self
            if member_username == self.settings.user_config.username:
                continue
                
            contact = await self.db_client.get_contact(member_username)
            if not contact or not contact.public_key:
                print(f"Skipping {member_username}: No public key found")
                continue
                
            try:
                encrypted_key = encrypt_message(contact.public_key.encode(), new_key)
                encrypted_key_b64 = base64.b64encode(encrypted_key).decode()
                
                msg = KircChatMessage(
                    type="channel_key_update",
                    sender=self.settings.user_config.username,
                    recipient=contact.username,
                    payload={
                        "channel": channel,
                        "key": encrypted_key_b64,
                        "key_id": key_id
                    }
                )
                
                target_topic = f"rpc-in-{contact.username}"
                await self.kafka_client.send_rpc(msg, topic=target_topic)
                count += 1
            except Exception as e:
                print(f"Failed to send key to {contact.username}: {e}")
        
        # Signal rotation via Redis
        await self.cache_client.publish_key_rotation(channel, key_id)
        self.notify(f"Rotated keys for #{channel}. Sent to {count} users.")

    async def handle_key_rotation(self, channel: str, key_id: str) -> None:
        """Handle notification of a key rotation."""
        self.notify(f"Key rotation detected for #{channel}. New key ID: {key_id}")
        self.active_key_ids[channel] = key_id
        # The actual key will be received via RPC (channel_key_update) if we are a member.

    async def handle_channel_event(self, channel: str, event_type: str, username: str) -> None:
        """Handle channel membership events."""
        if event_type == "join":
            self.notify(f"{username} joined #{channel}")
        elif event_type == "leave":
            self.notify(f"{username} left #{channel}")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle message submission."""
        content = event.value.strip()
        if not content:
            return

        message_list = self.query_one("#message-list", MessageList)
        
        # Optimistically add to UI
        await message_list.add_message(self.settings.user_config.username, content)
        event.input.clear()

        # Send to Kafka if connected
        if self.kafka_client and self.cache_client:
            try:
                channel = self.current_channel
                
                # 1. Find Leader
                leader = await self.cache_client.get_channel_leader(channel)
                if not leader:
                    # Claim leadership if none exists
                    success = await self.cache_client.register_channel_leader(channel)
                    if success:
                        leader = self.settings.user_config.username
                        self.notify(f"Claimed leadership of #{channel}")
                        if channel not in self.channel_keys:
                            self.channel_keys[channel] = {}
                            new_key = generate_symmetric_key()
                            key_id = str(uuid4())
                            self.channel_keys[channel][key_id] = new_key
                            self.active_key_ids[channel] = key_id
                    else:
                        leader = await self.cache_client.get_channel_leader(channel)
                
                if not leader:
                    self.notify("Error: No channel leader found", severity="error")
                    return

                # Encrypt content
                active_key_id = self.active_key_ids.get(channel)
                if active_key_id and channel in self.channel_keys and active_key_id in self.channel_keys[channel]:
                    key = self.channel_keys[channel][active_key_id]
                    encrypted_content = encrypt_symmetric(key, content)
                    final_content = base64.b64encode(encrypted_content).decode()
                    payload_extras = {"key_id": active_key_id}
                else:
                    final_content = content 
                    payload_extras = {}
                    if leader != self.settings.user_config.username:
                         self.notify("WARNING: Transmitting unencrypted", severity="warning")

                msg = KircChatMessage(
                    sender=self.settings.user_config.username,
                    content=final_content,
                    channel=channel,
                    payload={**payload_extras, "content": final_content, "channel": channel}
                )

                # If WE are the leader, we broadcast directly to our output
                if leader == self.settings.user_config.username:
                    await self.kafka_client.send_message(msg) # Sends to data-out
                else:
                    # Send to Leader's Inbox
                    target_topic = f"inbox-{leader}"
                    await self.kafka_client.send_message(msg, topic=target_topic)
                
            except Exception as e:
                self.notify(f"Failed to transmit: {e}", severity="error")
        else:
            self.notify("OFFLINE: Message not transmitted", severity="warning")
