"""Message types for Kafka communication using msgpack for compact serialization."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

import msgpack
from pydantic import BaseModel, Field


def _encode_extended(obj: Any) -> Any:
    """Encode extended types for msgpack."""
    if isinstance(obj, UUID):
        return {"__uuid__": str(obj)}
    if isinstance(obj, datetime):
        return {"__datetime__": obj.isoformat()}
    if isinstance(obj, Enum):
        return {"__enum__": obj.value}
    return obj


def _decode_extended(obj: Any) -> Any:
    """Decode extended types from msgpack."""
    if isinstance(obj, dict):
        if "__uuid__" in obj:
            return UUID(obj["__uuid__"])
        if "__datetime__" in obj:
            return datetime.fromisoformat(obj["__datetime__"])
        if "__enum__" in obj:
            return obj["__enum__"]
    return obj


class MessageType(str, Enum):
    """Types of messages that can be sent via Kafka."""

    # Data messages
    CHAT = "chat"
    DIRECT = "direct"
    BROADCAST = "broadcast"

    # RPC messages
    PING = "ping"
    PONG = "pong"
    PRESENCE = "presence"
    TYPING = "typing"
    ACK = "ack"


class Message(BaseModel):
    """Base message structure for all Kafka messages."""

    id: UUID = Field(default_factory=uuid4)
    type: MessageType
    sender: str = Field(description="Sender's username")
    recipient: str | None = Field(
        default=None, description="Recipient username (None for broadcast)"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)

    def to_bytes(self) -> bytes:
        """Serialize message to msgpack bytes."""
        data = self.model_dump(mode="python")
        return msgpack.packb(data, default=_encode_extended, strict_types=False)

    @classmethod
    def from_bytes(cls, data: bytes) -> "Message":
        """Deserialize message from msgpack bytes."""
        unpacked = msgpack.unpackb(data, object_hook=_decode_extended, raw=False)
        return cls.model_validate(unpacked)


class ChatMessage(Message):
    """A chat message with text content."""

    type: MessageType = MessageType.CHAT
    content: str = Field(description="Message text content")
    channel: str | None = Field(default=None, description="Channel name if applicable")


class DirectMessage(Message):
    """A direct message to a specific user."""

    type: MessageType = MessageType.DIRECT
    content: str = Field(description="Message text content")


class PresenceMessage(Message):
    """Presence update message."""

    type: MessageType = MessageType.PRESENCE
    status: str = Field(description="online, away, offline")


class TypingMessage(Message):
    """Typing indicator message."""

    type: MessageType = MessageType.TYPING
    is_typing: bool = Field(default=True)
