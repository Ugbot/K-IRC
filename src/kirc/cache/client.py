"""Async Valkey/Redis client for pub/sub and caching."""

import asyncio
from collections.abc import Callable
from typing import Any

import msgpack
import redis.asyncio as redis


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
        self._client: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._running = False
        self._presence_handlers: list[Callable[[str, str], Any]] = []
        self._typing_handlers: list[Callable[[str, str, bool], Any]] = []
        self._notification_handlers: list[Callable[[dict], Any]] = []

    async def connect(self) -> None:
        """Connect to Valkey/Redis."""
        self._client = redis.from_url(self._url, decode_responses=False)
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
            for handler in self._typing_handlers:
                try:
                    result = handler(
                        data.get("channel"),
                        data.get("username"),
                        data.get("is_typing", False),
                    )
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    print(f"Error in typing handler: {e}")

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
