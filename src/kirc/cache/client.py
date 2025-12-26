"""Async Valkey/Redis client for pub/sub and caching."""

import asyncio
import time
from collections.abc import Callable
from typing import Any

import msgpack
import valkey.asyncio as valkey


class CacheClient:
    """Async Valkey/Redis client for presence, typing indicators, and session cache.

    Uses Redis pub/sub for real-time notifications:
    - presence:{username} - Online/offline status
    - typing:{channel} - Typing indicators per channel
    - notify:{username} - Direct notifications
    """

    def __init__(self, url: str, username: str) -> None:
        """Initialize with Valkey/Redis connection URL."""
        self._url = url
        self._username = username
        self._client: valkey.Valkey | None = None
        self._pubsub: valkey.client.PubSub | None = None
        self._running = False
        self._presence_handlers: list[Callable[[str, str], Any]] = []
        self._typing_handlers: list[Callable[[str, str, bool], Any]] = []
        self._notification_handlers: list[Callable[[dict], Any]] = []
        self._rotation_handlers: list[Callable[[dict], Any]] = []
        self._channel_event_handlers: list[Callable[[str, dict], Any]] = []

    async def connect(self) -> None:
        """Connect to Valkey/Redis."""
        self._client = valkey.from_url(self._url, decode_responses=False)
        self._pubsub = self._client.pubsub()
        self._running = True

        # Subscribe to our notification channel
        await self._pubsub.subscribe(f"notify:{self._username}")

    async def disconnect(self) -> None:
        """Disconnect from Valkey/Redis."""
        self._running = False

        # Set offline status before disconnecting
        await self.set_presence("offline")

        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
            self._pubsub = None

        if self._client:
            await self._client.close()
            self._client = None

    # Presence
    async def set_presence(self, status: str, ttl_seconds: int = 300) -> None:
        """Set user presence status with TTL."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        key = f"presence:{self._username}"
        await self._client.setex(key, ttl_seconds, status.encode())

        # Publish presence change
        await self._client.publish(
            f"presence:{self._username}",
            msgpack.packb({"username": self._username, "status": status}),
        )

    async def get_presence(self, username: str) -> str:
        """Get user presence status."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        key = f"presence:{username}"
        status = await self._client.get(key)
        return status.decode() if status else "offline"

    async def refresh_presence(self, ttl_seconds: int = 300) -> None:
        """Refresh presence TTL to keep online."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        key = f"presence:{self._username}"
        await self._client.expire(key, ttl_seconds)

    def on_presence(self, handler: Callable[[str, str], Any]) -> None:
        """Register handler for presence changes. Handler receives (username, status)."""
        self._presence_handlers.append(handler)

    # Typing Indicators
    async def set_typing(self, channel: str, is_typing: bool = True, ttl_seconds: int = 5) -> None:
        """Set typing indicator for a channel."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        key = f"typing:{channel}:{self._username}"

        if is_typing:
            await self._client.setex(key, ttl_seconds, b"1")
        else:
            await self._client.delete(key)

        # Publish typing change
        await self._client.publish(
            f"typing:{channel}",
            msgpack.packb(
                {
                    "username": self._username,
                    "channel": channel,
                    "is_typing": is_typing,
                }
            ),
        )

    async def get_typing_users(self, channel: str) -> list[str]:
        """Get list of users currently typing in a channel."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        pattern = f"typing:{channel}:*"
        keys = await self._client.keys(pattern)

        users = []
        for key in keys:
            # Extract username from key
            key_str = key.decode() if isinstance(key, bytes) else key
            username = key_str.split(":")[-1]
            users.append(username)

        return users

    def on_typing(self, handler: Callable[[str, str, bool], Any]) -> None:
        """Register handler for typing changes. Handler receives (channel, username, is_typing)."""
        self._typing_handlers.append(handler)

    # Notifications
    async def send_notification(self, recipient: str, data: dict) -> None:
        """Send a notification to a user."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        await self._client.publish(
            f"notify:{recipient}",
            msgpack.packb(data),
        )

    def on_notification(self, handler: Callable[[dict], Any]) -> None:
        """Register handler for notifications."""
        self._notification_handlers.append(handler)

    # Pub/Sub subscription management
    async def subscribe_presence(self, username: str) -> None:
        """Subscribe to presence updates for a user."""
        if not self._pubsub:
            raise RuntimeError("Cache client not connected")
        await self._pubsub.subscribe(f"presence:{username}")

    async def subscribe_typing(self, channel: str) -> None:
        """Subscribe to typing updates for a channel."""
        if not self._pubsub:
            raise RuntimeError("Cache client not connected")
        await self._pubsub.subscribe(f"typing:{channel}")

    async def unsubscribe_presence(self, username: str) -> None:
        """Unsubscribe from presence updates."""
        if not self._pubsub:
            return
        await self._pubsub.unsubscribe(f"presence:{username}")

    async def unsubscribe_typing(self, channel: str) -> None:
        """Unsubscribe from typing updates."""
        if not self._pubsub:
            return
        await self._pubsub.unsubscribe(f"typing:{channel}")

    # Session cache
    async def cache_set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set a cached value with TTL."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        packed = msgpack.packb(value)
        await self._client.setex(f"cache:{self._username}:{key}", ttl_seconds, packed)

    async def cache_get(self, key: str) -> Any | None:
        """Get a cached value."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        data = await self._client.get(f"cache:{self._username}:{key}")
        if data:
            return msgpack.unpackb(data, raw=False)
        return None

    async def cache_delete(self, key: str) -> None:
        """Delete a cached value."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        await self._client.delete(f"cache:{self._username}:{key}")

    # Channel Leadership
    async def register_channel_leader(self, channel: str, ttl_seconds: int = 300) -> bool:
        """Try to register as the leader for a channel. Returns True if successful."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        key = f"channel:{channel}:leader"
        # NX=True means only set if not exists
        success = await self._client.set(key, self._username, ex=ttl_seconds, nx=True)
        
        # If we are already the leader, refresh TTL
        if not success:
            current_leader = await self._client.get(key)
            if current_leader and current_leader.decode() == self._username:
                await self._client.expire(key, ttl_seconds)
                return True
        
        return bool(success)

    async def get_channel_leader(self, channel: str) -> str | None:
        """Get the current leader of a channel."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        key = f"channel:{channel}:leader"
        leader = await self._client.get(key)
        return leader.decode() if leader else None

    async def resign_channel_leader(self, channel: str) -> None:
        """Resign leadership of a channel."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        key = f"channel:{channel}:leader"
        # Only delete if we are the leader
        current_leader = await self._client.get(key)
        if current_leader and current_leader.decode() == self._username:
            await self._client.delete(key)

    # Channel Keys (Symmetric Encryption)
    async def set_channel_key_for_user(self, channel: str, username: str, encrypted_key: bytes, ttl_seconds: int = 86400) -> None:
        """Store an encrypted channel key for a specific user."""
        if not self._client:
            raise RuntimeError("Cache client not connected")
            
        key = f"channel:{channel}:keys"
        # We use a hash where field is username and value is the encrypted key
        # But to support TTL, maybe we should use separate keys?
        # Redis Hashes don't support TTL per field.
        # So let's use `channel:{channel}:key:{username}`
        
        user_key_path = f"channel:{channel}:key:{username}"
        await self._client.setex(user_key_path, ttl_seconds, encrypted_key)

    async def get_channel_key(self, channel: str) -> bytes | None:
        """Get the encrypted channel key for the current user."""
        if not self._client:
            raise RuntimeError("Cache client not connected")
            
        user_key_path = f"channel:{channel}:key:{self._username}"
        key_data = await self._client.get(user_key_path)
        return key_data

    # Key Rotation Signaling
    async def publish_key_rotation(self, channel: str, key_id: str, start_message_id: str | None = None) -> None:
        """Signal that a key rotation has occurred."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        await self._client.publish(
            f"rotation:{channel}",
            msgpack.packb({
                "channel": channel,
                "key_id": key_id,
                "start_message_id": start_message_id,
                "timestamp": time.time()
            })
        )

    def on_key_rotation(self, handler: Callable[[dict], Any]) -> None:
        """Register handler for key rotation signals."""
        self._rotation_handlers.append(handler)

    async def subscribe_rotation(self, channel: str) -> None:
        """Subscribe to rotation signals for a channel."""
        if not self._pubsub:
            raise RuntimeError("Cache client not connected")
        await self._pubsub.subscribe(f"rotation:{channel}")

    # Channel Status & Events
    async def set_channel_status(self, channel: str, status: dict, ttl_seconds: int = 300) -> None:
        """Set channel status metadata."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        key = f"channel:{channel}:status"
        # Store as hash for easier field updates if needed, or just msgpack blob
        # Using msgpack blob for simplicity with setex
        await self._client.setex(key, ttl_seconds, msgpack.packb(status))

    async def get_channel_status(self, channel: str) -> dict | None:
        """Get channel status metadata."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        key = f"channel:{channel}:status"
        data = await self._client.get(key)
        if data:
            return msgpack.unpackb(data, raw=False)
        return None

    async def publish_channel_event(self, channel: str, event_type: str, payload: dict) -> None:
        """Publish a generic event to the channel's control plane."""
        if not self._client:
            raise RuntimeError("Cache client not connected")

        await self._client.publish(
            f"channel:{channel}:events",
            msgpack.packb({
                "type": event_type,
                "payload": payload,
                "sender": self._username
            })
        )

    async def subscribe_channel_events(self, channel: str) -> None:
        """Subscribe to channel control plane events."""
        if not self._pubsub:
            raise RuntimeError("Cache client not connected")
        await self._pubsub.subscribe(f"channel:{channel}:events")

    def on_channel_event(self, handler: Callable[[str, dict], Any]) -> None:
        """Register handler for channel events. Handler receives (channel, event_data)."""
        self._channel_event_handlers.append(handler)

    # Channel Membership
    async def join_channel(self, channel: str) -> None:
        """Join a channel (add self to members set)."""
        if not self._client:
            raise RuntimeError("Cache client not connected")
        
        key = f"channel:{channel}:members"
        await self._client.sadd(key, self._username)
        # Publish join event
        await self.publish_channel_event(channel, "join", {"username": self._username})

    async def leave_channel(self, channel: str) -> None:
        """Leave a channel (remove self from members set)."""
        if not self._client:
            raise RuntimeError("Cache client not connected")
            
        key = f"channel:{channel}:members"
        await self._client.srem(key, self._username)
        # Publish leave event
        await self.publish_channel_event(channel, "leave", {"username": self._username})

    async def get_channel_members(self, channel: str) -> list[str]:
        """Get all members of a channel."""
        if not self._client:
            raise RuntimeError("Cache client not connected")
            
        key = f"channel:{channel}:members"
        members = await self._client.smembers(key)
        return [m.decode() for m in members]

    async def kick_member(self, channel: str, username: str) -> None:
        """Kick a member from the channel (Leader only)."""
        if not self._client:
            raise RuntimeError("Cache client not connected")
            
        key = f"channel:{channel}:members"
        await self._client.srem(key, username)
        # Publish kick event
        await self.publish_channel_event(channel, "kick", {"username": username})

    # Pub/Sub message loop
    async def _handle_message(self, message: dict) -> None:
        """Handle incoming pub/sub message."""
        if message["type"] != "message":
            return

        channel = message["channel"]
        if isinstance(channel, bytes):
            channel = channel.decode()

        data = message["data"]
        if isinstance(data, bytes):
            try:
                data = msgpack.unpackb(data, raw=False)
            except Exception:
                return

        if channel.startswith("presence:"):
            for handler in self._presence_handlers:
                try:
                    result = handler(data.get("username"), data.get("status"))
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    print(f"Error in presence handler: {e}")

        elif channel.startswith("typing:"):
            # typing:{channel}
            chan_name = data.get("channel")
            user = data.get("username")
            is_typing = data.get("is_typing", False)
            for handler in self._typing_handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(chan_name, user, is_typing)
                else:
                    handler(chan_name, user, is_typing)
                    
        elif channel.startswith("rotation:"):
            # rotation:{channel}
            # data is already unpacked dict
            for handler in self._rotation_handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)

        elif "events" in channel and channel.startswith("channel:"):
            # channel:{channel}:events
            # Extract channel name: channel:NAME:events
            parts = channel.split(":")
            if len(parts) >= 3:
                chan_name = parts[1]
                # data is already unpacked dict
                for handler in self._channel_event_handlers:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(chan_name, data)
                    else:
                        handler(chan_name, data)

        elif channel.startswith("notify:"):
            for handler in self._notification_handlers:
                try:
                    result = handler(data)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    print(f"Error in notification handler: {e}")

    async def run(self) -> None:
        """Run the pub/sub message loop."""
        if not self._pubsub:
            raise RuntimeError("Cache client not connected")

        while self._running:
            try:
                message = await self._pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0,
                )
                if message:
                    await self._handle_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in pub/sub loop: {e}")
                await asyncio.sleep(1)

    async def __aenter__(self) -> "CacheClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()
