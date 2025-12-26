import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from kirc.config import load_settings
from kirc.db.client import DatabaseClient
from kirc.db.models import Contact, Channel, Message, ServiceConfig, ServiceType, UserProfile
from kirc.kafka.client import KafkaClient
from kirc.kafka.messages import ChatMessage, MessageType

async def create_profile(db: DatabaseClient, settings):
    # Ensure a user profile exists
    profile = await db.get_user_profile()
    if not profile:
        profile = UserProfile(
            id=uuid4(),
            username=settings.user_config.username,
            display_name=settings.user_config.display_name,
            public_key=await db._load_key(settings.user_config.private_key_path.replace('.pem', '.pub')),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await db.save_user_profile(profile)
    return profile

async def create_contacts(db: DatabaseClient, settings):
    contacts = []
    # Create two dummy contacts (bob and carol)
    for name in ["bob", "carol"]:
        contact = Contact(
            id=uuid4(),
            username=name,
            display_name=name.title(),
            public_key="dummy-public-key",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await db.save_contact(contact)
        contacts.append(contact)
    return contacts

async def create_channels(db: DatabaseClient):
    channels = []
    for name in ["NET_RUNNERS", "BLACK_ICE", "GHOST_IN_SHELL"]:
        channel = Channel(
            name=name,
            description=f"Demo channel {name}",
            is_joined=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await db.save_channel(channel)
        channels.append(channel)
    return channels

async def publish_messages(kafka: KafkaClient, settings, channels, contacts):
    # Publish a few chat messages to each channel
    for channel in channels:
        for i in range(3):
            msg = ChatMessage(
                type=MessageType.CHAT,
                sender=settings.user_config.username,
                recipient=None,
                channel=channel.name,
                content=f"Test message {i+1} in {channel.name}",
                timestamp=datetime.now(timezone.utc),
                payload={},
            )
            await kafka.produce(msg)
        # Simulate a direct message to each contact
        for contact in contacts:
            dm = ChatMessage(
                type=MessageType.DIRECT,
                sender=settings.user_config.username,
                recipient=contact.username,
                channel=None,
                content=f"Hello {contact.username}!",
                timestamp=datetime.now(timezone.utc),
                payload={},
            )
            await kafka.produce(dm)

async def main():
    settings = load_settings()
    db = DatabaseClient(dsn=settings.postgres.uri)
    await db.connect()
    await create_profile(db, settings)
    contacts = await create_contacts(db, settings)
    channels = await create_channels(db)
    # Initialize Kafka client (will connect to the personal inbox topics)
    kafka = KafkaClient(settings=settings)
    await kafka.connect()
    await publish_messages(kafka, settings, channels, contacts)
    await kafka.disconnect()
    await db.disconnect()
    print("Test data generation complete.")

if __name__ == "__main__":
    asyncio.run(main())
