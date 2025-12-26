"""Async PostgreSQL client using asyncpg."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import asyncpg
import msgpack

from kirc.db.models import Channel, Contact, Message, ServiceConfig, ServiceType, UserProfile


class DatabaseClient:
    """Async PostgreSQL client for K-IRC data storage."""

    def __init__(self, dsn: str) -> None:
        """Initialize with PostgreSQL connection string."""
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Create connection pool."""
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=10)

    async def disconnect(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def initialize_schema(self) -> None:
        """Create database tables if they don't exist."""
        schema_path = Path(__file__).parent / "schema.sql"
        schema_sql = schema_path.read_text()

        async with self._pool.acquire() as conn:
            await conn.execute(schema_sql)

    # Service Configs
    async def save_service_config(self, config: ServiceConfig) -> ServiceConfig:
        """Insert or update a service configuration."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO service_configs
                    (id, service_type, name, host, port, username, password,
                     ssl_enabled, ssl_ca_cert, ssl_client_cert, ssl_client_key,
                     extra_config, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ON CONFLICT (id) DO UPDATE SET
                    service_type = EXCLUDED.service_type,
                    name = EXCLUDED.name,
                    host = EXCLUDED.host,
                    port = EXCLUDED.port,
                    username = EXCLUDED.username,
                    password = EXCLUDED.password,
                    ssl_enabled = EXCLUDED.ssl_enabled,
                    ssl_ca_cert = EXCLUDED.ssl_ca_cert,
                    ssl_client_cert = EXCLUDED.ssl_client_cert,
                    ssl_client_key = EXCLUDED.ssl_client_key,
                    extra_config = EXCLUDED.extra_config,
                    updated_at = NOW()
                """,
                config.id,
                config.service_type.value,
                config.name,
                config.host,
                config.port,
                config.username,
                config.password,
                config.ssl_enabled,
                config.ssl_ca_cert,
                config.ssl_client_cert,
                config.ssl_client_key,
                config.extra_config,
                config.created_at,
                config.updated_at,
            )
        return config

    async def get_service_config(self, service_type: ServiceType) -> ServiceConfig | None:
        """Get service config by type."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM service_configs WHERE service_type = $1",
                service_type.value,
            )
            if row:
                return ServiceConfig(
                    id=row["id"],
                    service_type=ServiceType(row["service_type"]),
                    name=row["name"],
                    host=row["host"],
                    port=row["port"],
                    username=row["username"],
                    password=row["password"],
                    ssl_enabled=row["ssl_enabled"],
                    ssl_ca_cert=row["ssl_ca_cert"],
                    ssl_client_cert=row["ssl_client_cert"],
                    ssl_client_key=row["ssl_client_key"],
                    extra_config=row["extra_config"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            return None

    async def get_all_service_configs(self) -> list[ServiceConfig]:
        """Get all service configurations."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM service_configs")
            return [
                ServiceConfig(
                    id=row["id"],
                    service_type=ServiceType(row["service_type"]),
                    name=row["name"],
                    host=row["host"],
                    port=row["port"],
                    username=row["username"],
                    password=row["password"],
                    ssl_enabled=row["ssl_enabled"],
                    ssl_ca_cert=row["ssl_ca_cert"],
                    ssl_client_cert=row["ssl_client_cert"],
                    ssl_client_key=row["ssl_client_key"],
                    extra_config=row["extra_config"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    # User Profile
    async def save_user_profile(self, profile: UserProfile) -> UserProfile:
        """Insert or update user profile."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO user_profiles
                    (id, username, display_name, public_key, avatar_url,
                     status, bio, is_public, quota_bytes_per_day, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (username) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    public_key = EXCLUDED.public_key,
                    avatar_url = EXCLUDED.avatar_url,
                    status = EXCLUDED.status,
                    bio = EXCLUDED.bio,
                    is_public = EXCLUDED.is_public,
                    quota_bytes_per_day = EXCLUDED.quota_bytes_per_day,
                    updated_at = NOW()
                """,
                profile.id,
                profile.username,
                profile.display_name,
                profile.public_key,
                profile.avatar_url,
                profile.status,
                profile.bio,
                profile.is_public,
                profile.quota_bytes_per_day,
                profile.created_at,
                profile.updated_at,
            )
        return profile

    async def get_user_profile(self) -> UserProfile | None:
        """Get the local user profile (there should only be one)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM user_profiles LIMIT 1")
            if row:
                return UserProfile(
                    id=row["id"],
                    username=row["username"],
                    display_name=row["display_name"],
                    public_key=row["public_key"],
                    avatar_url=row["avatar_url"],
                    status=row["status"],
                    bio=row["bio"],
                    is_public=row["is_public"],
                    quota_bytes_per_day=row["quota_bytes_per_day"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            return None

    # Contacts
    async def save_contact(self, contact: Contact) -> Contact:
        """Insert or update a contact."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO contacts
                    (id, username, display_name, kafka_bootstrap_servers,
                     public_key, notes, is_blocked, last_seen, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (username) DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    kafka_bootstrap_servers = EXCLUDED.kafka_bootstrap_servers,
                    public_key = EXCLUDED.public_key,
                    notes = EXCLUDED.notes,
                    is_blocked = EXCLUDED.is_blocked,
                    last_seen = EXCLUDED.last_seen,
                    updated_at = NOW()
                """,
                contact.id,
                contact.username,
                contact.display_name,
                contact.kafka_bootstrap_servers,
                contact.public_key,
                contact.notes,
                contact.is_blocked,
                contact.last_seen,
                contact.created_at,
                contact.updated_at,
            )
        return contact

    async def get_contact(self, username: str) -> Contact | None:
        """Get a contact by username."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM contacts WHERE username = $1",
                username,
            )
            if row:
                return Contact(
                    id=row["id"],
                    username=row["username"],
                    display_name=row["display_name"],
                    kafka_bootstrap_servers=row["kafka_bootstrap_servers"],
                    public_key=row["public_key"],
                    notes=row["notes"],
                    is_blocked=row["is_blocked"],
                    last_seen=row["last_seen"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            return None

    async def get_all_contacts(self, include_blocked: bool = False) -> list[Contact]:
        """Get all contacts."""
        async with self._pool.acquire() as conn:
            if include_blocked:
                rows = await conn.fetch("SELECT * FROM contacts ORDER BY username")
            else:
                rows = await conn.fetch(
                    "SELECT * FROM contacts WHERE is_blocked = FALSE ORDER BY username"
                )
            return [
                Contact(
                    id=row["id"],
                    username=row["username"],
                    display_name=row["display_name"],
                    kafka_bootstrap_servers=row["kafka_bootstrap_servers"],
                    public_key=row["public_key"],
                    notes=row["notes"],
                    is_blocked=row["is_blocked"],
                    last_seen=row["last_seen"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    async def delete_contact(self, username: str) -> bool:
        """Delete a contact."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM contacts WHERE username = $1",
                username,
            )
            return result == "DELETE 1"

    # Channels
    async def save_channel(self, channel: Channel) -> Channel:
        """Insert or update a channel."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO channels
                    (name, description, is_joined, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    is_joined = EXCLUDED.is_joined,
                    updated_at = NOW()
                """,
                channel.name,
                channel.description,
                channel.is_joined,
                channel.created_at,
                channel.updated_at,
            )
        return channel

    async def get_channel(self, name: str) -> Channel | None:
        """Get a channel by name."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM channels WHERE name = $1",
                name,
            )
            if row:
                return Channel(
                    name=row["name"],
                    description=row["description"],
                    is_joined=row["is_joined"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            return None

    async def get_all_channels(self, joined_only: bool = True) -> list[Channel]:
        """Get all channels."""
        async with self._pool.acquire() as conn:
            if joined_only:
                rows = await conn.fetch("SELECT * FROM channels WHERE is_joined = TRUE ORDER BY name")
            else:
                rows = await conn.fetch("SELECT * FROM channels ORDER BY name")
            return [
                Channel(
                    name=row["name"],
                    description=row["description"],
                    is_joined=row["is_joined"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    async def delete_channel(self, name: str) -> bool:
        """Delete a channel."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM channels WHERE name = $1",
                name,
            )
            return result == "DELETE 1"

    # Messages
    async def save_message(self, message: Message) -> Message:
        """Save a message to history."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO messages
                    (id, message_type, sender, recipient, channel,
                     content, timestamp, is_outbound, is_read, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (id) DO NOTHING
                """,
                message.id,
                message.message_type,
                message.sender,
                message.recipient,
                message.channel,
                message.content,
                message.timestamp,
                message.is_outbound,
                message.is_read,
                message.created_at,
            )
        return message

    async def get_messages(
        self,
        channel: str | None = None,
        contact: str | None = None,
        limit: int = 100,
        before: datetime | None = None,
    ) -> list[Message]:
        """Get messages, optionally filtered by channel or contact."""
        async with self._pool.acquire() as conn:
            conditions = []
            params: list[Any] = []
            param_idx = 1

            if channel:
                conditions.append(f"channel = ${param_idx}")
                params.append(channel)
                param_idx += 1
            elif contact:
                conditions.append(
                    f"((sender = ${param_idx} AND is_outbound = FALSE) OR "
                    f"(recipient = ${param_idx} AND is_outbound = TRUE))"
                )
                params.append(contact)
                param_idx += 1

            if before:
                conditions.append(f"timestamp < ${param_idx}")
                params.append(before)
                param_idx += 1

            where_clause = " AND ".join(conditions) if conditions else "TRUE"
            params.append(limit)

            rows = await conn.fetch(
                f"""
                SELECT * FROM messages
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ${param_idx}
                """,
                *params,
            )

            return [
                Message(
                    id=row["id"],
                    message_type=row["message_type"],
                    sender=row["sender"],
                    recipient=row["recipient"],
                    channel=row["channel"],
                    content=row["content"],
                    timestamp=row["timestamp"],
                    is_outbound=row["is_outbound"],
                    is_read=row["is_read"],
                    created_at=row["created_at"],
                )
                for row in reversed(rows)  # Return in chronological order
            ]

    async def mark_messages_read(
        self, contact: str | None = None, channel: str | None = None
    ) -> int:
        """Mark messages as read."""
        async with self._pool.acquire() as conn:
            if channel:
                result = await conn.execute(
                    "UPDATE messages SET is_read = TRUE WHERE channel = $1 AND is_read = FALSE",
                    channel,
                )
            elif contact:
                result = await conn.execute(
                    "UPDATE messages SET is_read = TRUE WHERE sender = $1 AND is_read = FALSE",
                    contact,
                )
            else:
                result = await conn.execute(
                    "UPDATE messages SET is_read = TRUE WHERE is_read = FALSE"
                )
            # Parse "UPDATE N" to get count
            return int(result.split()[-1]) if result else 0

    # Channel Keys
    async def save_channel_key(self, channel_name: str, key_id: str, encrypted_key: str) -> None:
        """Save an encrypted channel key."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO channel_keys (channel_name, key_id, encrypted_key)
                VALUES ($1, $2, $3)
                ON CONFLICT (channel_name, key_id) DO UPDATE SET
                    encrypted_key = EXCLUDED.encrypted_key
                """,
                channel_name,
                key_id,
                encrypted_key,
            )

    async def get_channel_keys(self, channel_name: str) -> dict[str, str]:
        """Get all keys for a channel."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT key_id, encrypted_key FROM channel_keys WHERE channel_name = $1",
                channel_name,
            )
            return {row["key_id"]: row["encrypted_key"] for row in rows}

    async def __aenter__(self) -> "DatabaseClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()
