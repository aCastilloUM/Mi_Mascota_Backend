# services/auth-svc/app/events/kafka.py
import asyncio
import json
import logging
from typing import Optional, Sequence, Tuple

from aiokafka import AIOKafkaProducer
from app.core.config import settings

logger = logging.getLogger(__name__)

class KafkaBus:
    """
    Event bus usando Kafka para publicar eventos del dominio.
    Singleton que se inicia con el ciclo de vida de FastAPI.
    """
    def __init__(self) -> None:
        self._producer: Optional[AIOKafkaProducer] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Inicia el productor de Kafka"""
        async with self._lock:
            if self._producer:
                return
            self._producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: (k.encode("utf-8") if isinstance(k, str) else k),
            )
            await self._producer.start()
            logger.info("kafka_producer_started", extra={"bootstrap": settings.kafka_bootstrap_servers})

    async def stop(self):
        """Detiene el productor de Kafka"""
        async with self._lock:
            if self._producer:
                await self._producer.stop()
                self._producer = None
                logger.info("kafka_producer_stopped")

    async def publish(
        self,
        topic: str,
        *,
        key: Optional[str],
        value: dict,
        headers: Optional[Sequence[Tuple[str, bytes]]] = None,
    ):
        """
        Publica un evento a Kafka.
        
        Args:
            topic: Nombre del topic de Kafka
            key: Key de particionamiento (ej: user_id)
            value: Payload del evento (dict que se serializa a JSON)
            headers: Headers del mensaje Kafka
        """
        if not self._producer:
            raise RuntimeError("Kafka producer not started")
        await self._producer.send_and_wait(topic, key=key, value=value, headers=headers or [])

# Instancia global del bus
bus = KafkaBus()
