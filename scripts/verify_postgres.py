import asyncio
import asyncpg

async def test_postgres():
    dsn = "postgres://avnadmin:PASSWORD@HOST:PORT/defaultdb?sslmode=require"
    print(f"Connecting to PostgreSQL at {dsn.split('@')[1]}...")
    
    try:
        conn = await asyncpg.connect(dsn)
        version = await conn.fetchval("SELECT VERSION()")
        print(f"✅ Successfully connected to Aiven PostgreSQL!")
        print(f"Version: {version}")
        await conn.close()
    except Exception as e:
        print(f"❌ Failed to connect to PostgreSQL: {e}")

if __name__ == "__main__":
    asyncio.run(test_postgres())
