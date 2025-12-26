import asyncio
import redis.asyncio as redis

async def test_valkey():
    # Actual Aiven URI (using rediss:// as valkey library requires it)
    url = "rediss://default:PASSWORD@HOST:PORT"
    print(f"Connecting to Valkey at {url.split('@')[-1]}...")
    
    try:
        client = redis.from_url(url)
        info = await client.info()
        print(f"✅ Successfully connected to Aiven Valkey!")
        print(f"Redis Version: {info.get('redis_version')}")
        await client.close()
    except Exception as e:
        print(f"❌ Failed to connect to Valkey: {e}")

if __name__ == "__main__":
    asyncio.run(test_valkey())
