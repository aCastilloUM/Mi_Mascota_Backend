from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import orjson
from aiokafka import AIOKafkaProducer

from app.core.config import settings

logger = logging.getLogger(__name__)

_producer: Optional[AIOKafkaProducer] = None
_started: bool = False


def _reset_state() -> None:
    global _producer, _started
    _producer = None
    _started = False


def _value_serializer(payload: Dict[str, Any]) -> bytes:
    return orjson.dumps(payload)


def _key_serializer(key: Any) -> Optional[bytes]:
    if key is None:
        return None
    if isinstance(key, bytes):
        return key
    return str(key).encode("utf-8")


async def get_producer() -> AIOKafkaProducer:
    if not settings.KAFKA_ENABLED:
        raise RuntimeError("Kafka is disabled")

    global _producer, _started

    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP,
            client_id=settings.KAFKA_CLIENT_ID,
            value_serializer=_value_serializer,
            key_serializer=_key_serializer,
            acks="all",
            linger_ms=10,
            retry_backoff_ms=200,
            request_timeout_ms=30000,
        )

    if not _started:
        try:
            await _producer.start()
        except Exception:
            logger.exception(
                "Kafka producer start failed (bootstrap=%s)",
                settings.KAFKA_BOOTSTRAP,
            )
            await stop_producer()
            raise
        else:
            _started = True
            logger.info(
                "Kafka producer started (bootstrap=%s)",
                settings.KAFKA_BOOTSTRAP,
            )

    return _producer


async def stop_producer() -> None:
    global _producer, _started

    if _producer is not None and _started:
        try:
            await _producer.stop()
            logger.info("Kafka producer stopped")
        except Exception:
            logger.exception("Kafka producer stop failed")
        finally:
            _reset_state()
    else:
        _reset_state()


async def send_event(
    topic: str,
    key: Optional[str],
    value: Dict[str, Any],
    *,
    raise_on_error: bool = False,
) -> None:
    if not settings.KAFKA_ENABLED:
        logger.debug(
            "Kafka disabled; skipping event topic=%s key=%s",
            topic,
            key,
        )
        return

    try:
        producer = await get_producer()
        await producer.send_and_wait(topic, value=value, key=key)
        logger.debug("Kafka event sent | topic=%s key=%s", topic, key)
    except Exception as exc:
        logger.exception("Failed to send Kafka event | topic=%s key=%s", topic, key)
        if raise_on_error:
            raise exc
