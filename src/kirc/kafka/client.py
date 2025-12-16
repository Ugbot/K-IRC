"""Async Kafka client for actor mailbox pattern."""

import asyncio
import ssl
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError

from kirc.kafka.messages import Message


class KafkaClient:
    """Async Kafka client implementing actor mailbox pattern.

    Topics:
    - data-in: Incoming messages (inbox)
    - data-out: Outgoing messages (outbox)
    - rpc-in: Incoming RPC requests
    - rpc-out: Outgoing RPC responses
    """

    def __init__(
        self,
        bootstrap_servers: str,
        username: str,
        ssl_cafile: str | Path,
        ssl_certfile: str | Path,
        ssl_keyfile: str | Path,
        topic_data_in: str = "data-in",
        topic_data_out: str = "data-out",
        topic_rpc_in: str = "rpc-in",
        topic_rpc_out: str = "rpc-out",
    ) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.username = username
        self.topic_data_in = topic_data_in
        self.topic_data_out = topic_data_out
        self.topic_rpc_in = topic_rpc_in
        self.topic_rpc_out = topic_rpc_out

        self._ssl_context = self._create_ssl_context(ssl_cafile, ssl_certfile, ssl_keyfile)

        self._producer: AIOKafkaProducer | None = None
        self._consumer_data: AIOKafkaConsumer | None = None
        self._consumer_rpc: AIOKafkaConsumer | None = None
        self._running = False
        self._message_handlers: list[Callable[[Message], Any]] = []
        self._rpc_handlers: list[Callable[[Message], Any]] = []
        self._pending_requests: dict[str, asyncio.Future] = {}

    def _create_ssl_context(
        self,
        cafile: str | Path,
        certfile: str | Path,
        keyfile: str | Path,
    ) -> ssl.SSLContext:
        """Create SSL context for Aiven Kafka connection."""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=str(cafile))
        context.load_cert_chain(certfile=str(certfile), keyfile=str(keyfile))
        context.check_hostname = True
        return context

    async def connect(self) -> None:
        """Connect producer and consumers to Kafka."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            security_protocol="SSL",
            ssl_context=self._ssl_context,
        )
        await self._producer.start()

        # Main consumer for our own inbox
        self._consumer_data = AIOKafkaConsumer(
            self.topic_data_in,
            bootstrap_servers=self.bootstrap_servers,
            security_protocol="SSL",
            ssl_context=self._ssl_context,
            group_id=f"kirc-{self.username}-data",
            auto_offset_reset="latest",
        )
        await self._consumer_data.start()

        self._consumer_rpc = AIOKafkaConsumer(
            self.topic_rpc_in,
            bootstrap_servers=self.bootstrap_servers,
            security_protocol="SSL",
            ssl_context=self._ssl_context,
            group_id=f"kirc-{self.username}-rpc",
            auto_offset_reset="latest",
        )
        await self._consumer_rpc.start()

        self._running = True

    async def subscribe_to_topic(self, topic: str) -> None:
        """Subscribe to an additional topic (e.g., a channel leader's output)."""
        if not self._consumer_data:
            raise RuntimeError("Kafka client not connected")
        
        # AIOKafkaConsumer.subscribe replaces the subscription, so we need to track all topics
        # But AIOKafkaConsumer also supports pattern subscription or adding partitions manually.
        # However, the simplest way with the high-level consumer is to update the subscription list.
        # Note: This might trigger a rebalance.
        
        current_topics = self._consumer_data.subscription() or set()
        if topic not in current_topics:
            new_topics = set(current_topics)
            new_topics.add(topic)
            self._consumer_data.subscribe(topics=list(new_topics))

    async def unsubscribe_from_topic(self, topic: str) -> None:
        """Unsubscribe from a topic."""
        if not self._consumer_data:
            raise RuntimeError("Kafka client not connected")
            
        current_topics = self._consumer_data.subscription() or set()
        if topic in current_topics:
            new_topics = set(current_topics)
            new_topics.remove(topic)
            # If no topics left, we can't pass empty list to subscribe usually, but let's see.
            # We always keep self.topic_data_in, so it should be fine.
            self._consumer_data.subscribe(topics=list(new_topics))

    async def disconnect(self) -> None:
        """Disconnect from Kafka."""
        self._running = False

        if self._producer:
            await self._producer.stop()
            self._producer = None

        if self._consumer_data:
            await self._consumer_data.stop()
            self._consumer_data = None

        if self._consumer_rpc:
            await self._consumer_rpc.stop()
            self._consumer_rpc = None

    def on_message(self, handler: Callable[[Message], Any]) -> None:
        """Register a handler for incoming data messages."""
        self._message_handlers.append(handler)

    def on_rpc(self, handler: Callable[[Message], Any]) -> None:
        """Register a handler for incoming RPC messages."""
        self._rpc_handlers.append(handler)

    async def send_message(self, message: Message, topic: str | None = None) -> None:
        """Send a message. If topic is None, sends to our own data-out."""
        if not self._producer:
            raise RuntimeError("Kafka client not connected")

        target_topic = topic or self.topic_data_out
        
        await self._producer.send_and_wait(
            target_topic,
            value=message.to_bytes(),
            key=message.sender.encode("utf-8"),
        )

    async def send_rpc(self, message: Message, topic: str | None = None) -> None:
        """Send an RPC message."""
        if not self._producer:
            raise RuntimeError("Kafka client not connected")

        target_topic = topic or self.topic_rpc_out

        await self._producer.send_and_wait(
            target_topic,
            value=message.to_bytes(),
            key=message.sender.encode("utf-8"),
        )

    async def request(self, message: Message, topic: str | None = None, timeout: float = 10.0) -> Message:
        """Send an RPC request and wait for a response."""
        if not message.correlation_id:
            message.correlation_id = uuid4()
        
        future = asyncio.Future()
        self._pending_requests[str(message.correlation_id)] = future
        
        try:
            await self.send_rpc(message, topic)
            return await asyncio.wait_for(future, timeout)
        finally:
            self._pending_requests.pop(str(message.correlation_id), None)

    async def _consume_data(self) -> AsyncIterator[Message]:
        """Consume messages from data-in topic."""
        if not self._consumer_data:
            raise RuntimeError("Kafka client not connected")

        async for record in self._consumer_data:
            try:
                message = Message.from_bytes(record.value)
                yield message
            except Exception as e:
                # Log and skip malformed messages
                print(f"Error parsing message: {e}")

    async def _consume_rpc(self) -> AsyncIterator[Message]:
        """Consume messages from rpc-in topic."""
        if not self._consumer_rpc:
            raise RuntimeError("Kafka client not connected")

        async for record in self._consumer_rpc:
            try:
                message = Message.from_bytes(record.value)
                yield message
            except Exception as e:
                print(f"Error parsing RPC message: {e}")

    async def _run_data_consumer(self) -> None:
        """Run the data consumer loop."""
        async for message in self._consume_data():
            if not self._running:
                break
            for handler in self._message_handlers:
                try:
                    result = handler(message)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    print(f"Error in message handler: {e}")

    async def _run_rpc_consumer(self) -> None:
        """Run the RPC consumer loop."""
        async for message in self._consume_rpc():
            if not self._running:
                break
            
            # Check if this is a response to a pending request
            if message.correlation_id and str(message.correlation_id) in self._pending_requests:
                future = self._pending_requests[str(message.correlation_id)]
                if not future.done():
                    future.set_result(message)
                continue

            # Otherwise, dispatch to handlers
            for handler in self._rpc_handlers:
                try:
                    result = handler(message)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    print(f"Error in RPC handler: {e}")

    async def run(self) -> None:
        """Run both consumer loops concurrently."""
        await asyncio.gather(
            self._run_data_consumer(),
            self._run_rpc_consumer(),
        )

    async def __aenter__(self) -> "KafkaClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.disconnect()
