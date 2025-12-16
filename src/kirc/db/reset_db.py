import asyncio
import os
from kirc.db.client import DatabaseClient
from kirc.config import load_settings

async def reset_messages_table():
    settings = load_settings()
    client = DatabaseClient(settings.postgres.uri)
    await client.connect()
    print("Dropping messages table...")
    async with client._pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS messages")
    print("Messages table dropped. It will be recreated with new schema on next run.")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(reset_messages_table())
