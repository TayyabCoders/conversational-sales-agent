"""
Messaging infrastructure with RabbitMQ and Kafka clients
"""
from typing import Any, Dict, Optional, List
import json
import asyncio
from aio_pika import connect_robust, Message, IncomingMessage, DeliveryMode, ExchangeType
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from structlog import get_logger

logger = get_logger(__name__)


class RabbitMQClient:
    """RabbitMQ client for message queuing"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5672,
        username: str = "admin",
        password: str = "admin",
        virtual_host: str = "/",
        max_connections: int = 10,
        max_channels: int = 100,
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.max_connections = max_connections
        self.max_channels = max_channels
        
        # Connection and channel
        self.connection = None
        self.channel = None
        self._connected = False
    
    async def connect(self) -> None:
        """Initialize RabbitMQ connection"""
        try:
            logger.info("Connecting to RabbitMQ...")
            
            # Build connection URL
            connection_url = (
                f"amqp://{self.username}:{self.password}"
                f"@{self.host}:{self.port}/{self.virtual_host}"
            )
            
            # Connect to RabbitMQ
            self.connection = await connect_robust(
                connection_url,
                timeout=30,
                client_properties={
                    "connection_name": "fastapi-app",
                    "product": "FastAPI App",
                    "version": "0.1.0",
                }
            )
            
            # Create channel
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            
            self._connected = True
            logger.info("RabbitMQ connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close RabbitMQ connection"""
        try:
            logger.info("Disconnecting from RabbitMQ...")
            
            if self.channel:
                await self.channel.close()
                self.channel = None
            
            if self.connection:
                await self.connection.close()
                self.connection = None
            
            self._connected = False
            logger.info("RabbitMQ connection closed successfully")
            
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    async def publish(
        self,
        exchange: str,
        routing_key: str,
        message: Dict[str, Any],
        persistent: bool = True,
        priority: int = 0,
    ) -> bool:
        """Publish message to RabbitMQ"""
        if not self._connected:
            raise RuntimeError("RabbitMQ not connected")
        
        try:
            # Ensure exchange exists
            await self._ensure_exchange(exchange)
            
            # Create message
            message_body = json.dumps(message).encode()
            message_obj = Message(
                message_body,
                delivery_mode=DeliveryMode.PERSISTENT if persistent else DeliveryMode.NON_PERSISTENT,
                priority=priority,
                content_type="application/json",
            )
            
            # Publish message
            await self.channel.default_exchange.publish(
                message_obj,
                routing_key=routing_key,
            )
            
            logger.debug(f"Message published to {exchange}:{routing_key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message to {exchange}:{routing_key}: {e}")
            return False

    async def consume(
        self,
        exchange: str,
        queue_name: str,
        routing_keys: List[str],
        callback,
        durable: bool = True,
    ) -> None:
        """
        Consume messages from RabbitMQ
        """
        if not self._connected:
            raise RuntimeError("RabbitMQ not connected")

        # Declare exchange
        exchange_obj = await self.channel.declare_exchange(
            exchange,
            ExchangeType.TOPIC,
            durable=True,
        )

        # Declare queue
        queue = await self.channel.declare_queue(
            queue_name,
            durable=durable,
        )

        # Bind routing keys
        for routing_key in routing_keys:
            await queue.bind(exchange_obj, routing_key)

        logger.info(
            "RabbitMQ consumer started",
            exchange=exchange,
            queue=queue_name,
            routing_keys=routing_keys,
        )

        async def _on_message(message: IncomingMessage):
            async with message.process():
                try:
                    payload = json.loads(message.body.decode())
                    await callback(payload)
                except Exception as e:
                    logger.error("Message processing failed", error=str(e))
                    raise

        await queue.consume(_on_message)
    
 
    async def _ensure_exchange(self, exchange: str) -> None:
        """Ensure exchange exists"""
        try:
            await self.channel.declare_exchange(
                exchange,
                ExchangeType.TOPIC,
                durable=True,
            )
        except Exception as e:
            logger.warning(f"Failed to declare exchange {exchange}: {e}")
    
    @property
    def connected(self) -> bool:
        """Check if RabbitMQ is connected"""
        return self._connected
    
    def health_check(self) -> dict:
        """RabbitMQ health check"""
        return {
            "status": "healthy" if self._connected else "unhealthy",
            "host": self.host,
            "port": self.port,
            "virtual_host": self.virtual_host,
        }


class KafkaClient:
    """Kafka client for event streaming"""
    
    def __init__(
        self,
        bootstrap_servers: List[str],
        client_id: str = "fastapi-app",
        group_id: str = "fastapi-group",
        max_request_size: int = 1048576,
        request_timeout_ms: int = 30000,
        retry_backoff_ms: int = 100,
    ):
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self.group_id = group_id
        self.max_request_size = max_request_size
        self.request_timeout_ms = request_timeout_ms
        self.retry_backoff_ms = retry_backoff_ms
        
        # Producer and consumer
        self.producer: Optional[AIOKafkaProducer] = None
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._connected = False
    
    async def connect(self) -> None:
        """Initialize Kafka connection"""
        try:
            logger.info("Connecting to Kafka...")
            
            # Create producer
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id=self.client_id,
                max_request_size=self.max_request_size,
                request_timeout_ms=self.request_timeout_ms,
                retry_backoff_ms=self.retry_backoff_ms,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
            )
            
            # Start producer
            await self.producer.start()
            
            self._connected = True
            logger.info("Kafka connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Kafka connection"""
        try:
            logger.info("Disconnecting from Kafka...")
            
            if self.producer:
                await self.producer.stop()
                self.producer = None
            
            if self.consumer:
                await self.consumer.stop()
                self.consumer = None
            
            self._connected = False
            logger.info("Kafka connection closed successfully")
            
        except Exception as e:
            logger.error(f"Error disconnecting from Kafka: {e}")
    
    async def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        key: Optional[str] = None,
        partition: Optional[int] = None,
        timestamp_ms: Optional[int] = None,
    ) -> bool:
        """Publish message to Kafka topic"""
        if not self._connected:
            raise RuntimeError("Kafka not connected")
        
        try:
            # Send message
            await self.producer.send_and_wait(
                topic=topic,
                value=message,
                key=key,
                partition=partition,
                timestamp_ms=timestamp_ms,
            )
            
            logger.debug(f"Message published to topic {topic}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message to topic {topic}: {e}")
            return False
    
    async def create_consumer(
        self,
        topics: List[str],
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = True,
        auto_commit_interval_ms: int = 1000,
    ) -> AIOKafkaConsumer:
        """Create Kafka consumer"""
        if not self._connected:
            raise RuntimeError("Kafka not connected")
        
        try:
            consumer = AIOKafkaConsumer(
                *topics,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=enable_auto_commit,
                auto_commit_interval_ms=auto_commit_interval_ms,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
            )
            
            await consumer.start()
            logger.info(f"Kafka consumer created for topics: {topics}")
            return consumer
            
        except Exception as e:
            logger.error(f"Failed to create Kafka consumer: {e}")
            raise
    
    @property
    def connected(self) -> bool:
        """Check if Kafka is connected"""
        return self._connected
    
    def health_check(self) -> dict:
        """Kafka health check"""
        return {
            "status": "healthy" if self._connected else "unhealthy",
            "bootstrap_servers": self.bootstrap_servers,
            "client_id": self.client_id,
            "group_id": self.group_id,
        }
