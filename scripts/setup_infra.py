import asyncio
import sys
from pathlib import Path
from kafka.admin import KafkaAdminClient, NewTopic
from kirc.config import load_settings
from kirc.db.client import DatabaseClient

from kirc.crypto import generate_key_pair, save_key_to_file

async def setup_identity(settings):
    priv_path = Path(settings.user_config.private_key_path)
    pub_path = priv_path.with_suffix(".pub")
    
    print(f"Checking for identity keys at {priv_path}...")
    if not priv_path.exists():
        print(" - Identity keys not found. Generating new 2048-bit RSA pair...")
        priv_pem, pub_pem = generate_key_pair()
        save_key_to_file(priv_pem, str(priv_path))
        save_key_to_file(pub_pem, str(pub_path))
        print(f" - Keys generated and saved to {priv_path} and {pub_path}")
    else:
        print(" - Identity keys already exist.")
    return True

async def setup_db(settings):
    print(f"Initializing PostgreSQL schema at {settings.postgres.uri}...")
    try:
        client = DatabaseClient(dsn=settings.postgres.uri)
        await client.connect()
        await client.initialize_schema()
        print("PostgreSQL schema initialized successfully.")
        await client.disconnect()
        return True
    except Exception as e:
        print(f"PostgreSQL initialization failed: {e}")
        return False

def setup_kafka(settings):
    kafka_cfg = settings.kafka
    print(f"Initializing Kafka topics at {kafka_cfg.bootstrap_servers}...")
    try:
        admin = KafkaAdminClient(
            bootstrap_servers=kafka_cfg.bootstrap_servers,
            security_protocol=kafka_cfg.security_protocol,
            sasl_mechanism=kafka_cfg.sasl_mechanism,
            sasl_plain_username=kafka_cfg.sasl_plain_username,
            sasl_plain_password=kafka_cfg.sasl_plain_password,
            ssl_cafile=kafka_cfg.ssl_cafile,
            request_timeout_ms=10000,
        )
        
        topic_names = [
            kafka_cfg.topic_data_in,
            kafka_cfg.topic_data_out,
            kafka_cfg.topic_rpc_in,
            kafka_cfg.topic_rpc_out,
            f"inbox-{settings.user_config.username}",
            f"rpc-in-{settings.user_config.username}"
        ]
        
        # Remove duplicates and empty strings
        topic_names = list(set(filter(None, topic_names)))
        
        existing_topics = admin.list_topics()
        new_topics = []
        for name in topic_names:
            if name and name not in existing_topics:
                print(f" - Preparing topic: {name}")
                new_topics.append(NewTopic(name=name, num_partitions=2, replication_factor=1))
        
        if new_topics:
            admin.create_topics(new_topics=new_topics, validate_only=False)
            print(f"Successfully created {len(new_topics)} topics.")
        else:
            print("All Kafka topics already exist.")
            
        admin.close()
        return True
    except Exception as e:
        print(f"Kafka initialization failed: {e}")
        return False

async def main():
    settings = load_settings()
    
    print("--- K-IRC Infrastructure Setup ---")
    id_ok = await setup_identity(settings)
    db_ok = await setup_db(settings)
    kafka_ok = setup_kafka(settings)
    
    if id_ok and db_ok and kafka_ok:
        print("\nInfrastructure setup complete! You can now run 'uv run kirc'.")
    else:
        print("\nSetup encountered errors. Please check your configuration.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
