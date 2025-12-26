import asyncio
import ssl
from aiokafka import AIOKafkaProducer
from kirc.kafka.messages import ChatMessage

async def test_connection():
    bootstrap_servers = "kafka-kirc-ververica-65ab.c.aivencloud.com:16760"
    sasl_username = "avnadmin"
    sasl_password = "PASSWORD"
    ca_file = "certs/ca.pem"

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_file)
    
    print(f"Connecting to {bootstrap_servers}...")
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        security_protocol="SASL_SSL",
        sasl_mechanism="SCRAM-SHA-256",
        sasl_plain_username=sasl_username,
        sasl_plain_password=sasl_password,
        ssl_context=context,
    )
    
    try:
        await producer.start()
        print("✅ Successfully connected to Aiven Kafka!")
        
        msg = ChatMessage(
            sender="verifier",
            content="Connectivity Test",
            channel="SYSTEM"
        )
        
        await producer.send_and_wait("data-in", msg.to_bytes())
        print("✅ Successfully sent test message to 'data-in'")
        
    except Exception as e:
        print(f"❌ Failed to connect or send: {e}")
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(test_connection())
