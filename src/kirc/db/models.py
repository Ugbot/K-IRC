"""Database models for K-IRC configuration and message storage."""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ServiceType(str, Enum):
    """Types of services we store credentials for."""

    KAFKA = "kafka"
    POSTGRESQL = "postgresql"
    VALKEY = "valkey"


class ServiceConfig(BaseModel):
    """Service connection configuration stored in PostgreSQL."""

    id: UUID
    service_type: ServiceType
    name: str = Field(description="Human-readable service name")
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    ssl_enabled: bool = True
    ssl_ca_cert: str | None = Field(default=None, description="CA certificate PEM content")
    ssl_client_cert: str | None = Field(default=None, description="Client certificate PEM")
    ssl_client_key: str | None = Field(default=None, description="Client key PEM")
    extra_config: dict | None = Field(default=None, description="Service-specific config")
    created_at: datetime
    updated_at: datetime


class UserProfile(BaseModel):
    """User profile configuration."""

    id: UUID
    username: str = Field(description="Unique username identifier")
    display_name: str = Field(description="Display name shown in UI")
    public_key: str | None = Field(default=None, description="Public key for encryption")
    avatar_url: str | None = None
    status: str = Field(default="online", description="Current status")
    bio: str | None = None
    is_public: bool = Field(default=True, description="Whether profile is publicly discoverable")
    quota_bytes_per_day: int = Field(
        default=1024 * 1024, description="Daily quota for public access"
    )
    created_at: datetime
    updated_at: datetime


class SharedCredential(BaseModel):
    """Shared credential model for encrypted service access."""
    
    id: UUID
    service_type: ServiceType
    encrypted_data: str = Field(description="Base64 encoded encrypted connection string")
    owner_id: str = Field(description="Username of the owner")
    recipient_id: str = Field(description="Username of the recipient")
    created_at: datetime


class Contact(BaseModel):
    """A contact/peer in the user's contact list."""

    id: UUID
    username: str = Field(description="Contact's username")
    display_name: str | None = None
    kafka_bootstrap_servers: str = Field(description="Contact's Kafka endpoint")
    public_key: str | None = Field(default=None, description="Contact's public key")
    notes: str | None = None
    is_blocked: bool = False
    last_seen: datetime | None = None
    created_at: datetime
    updated_at: datetime


class Channel(BaseModel):
    """A channel joined by the user."""

    name: str = Field(description="Channel name")
    description: str | None = None
    is_joined: bool = True
    created_at: datetime
    updated_at: datetime


class Message(BaseModel):
    """Persisted message for long-term storage."""

    id: int
    message_type: str = Field(description="chat, direct, broadcast, etc.")
    sender: str
    recipient: str | None = None
    channel: str | None = None
    content: bytes = Field(description="msgpack-encoded message content")
    timestamp: datetime
    is_outbound: bool = Field(description="True if we sent this message")
    is_read: bool = False
    created_at: datetime
