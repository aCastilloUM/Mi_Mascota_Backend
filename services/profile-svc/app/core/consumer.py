from __future__ import annotations

import asyncio
import logging
from typing import Optional

import orjson
from aiokafka import AIOKafkaConsumer
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.profile import Profile

logger = logging.getLogger(__name__)


class UserVerifiedConsumer:
    def __init__(self) -> None:
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        if not settings.KAFKA_ENABLED:
            logger.info("Kafka disabled; consumer not started")
            return

        if self._consumer:
            return

        self._consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPIC_USER_VERIFIED,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP,
            group_id=f"{settings.KAFKA_CLIENT_ID}-user-verified",
            enable_auto_commit=True,
            auto_offset_reset="earliest",
            value_deserializer=lambda v: orjson.loads(v) if v else None,
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
        )

        await self._consumer.start()
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("user_verified_consumer_started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception:
                pass
            self._task = None

        if self._consumer:
            try:
                await self._consumer.stop()
            except Exception:
                logger.exception("consumer_stop_failed")
            finally:
                self._consumer = None

    async def _loop(self) -> None:
        assert self._consumer is not None
        try:
            async for msg in self._consumer:
                try:
                    await self._handle_message(msg.key, msg.value)
                except Exception:
                    logger.exception("failed_to_handle_user_verified_message")
                if not self._running:
                    break
        except asyncio.CancelledError:
            logger.debug("consumer loop cancelled")
        except Exception:
            logger.exception("consumer_loop_error")

    async def _handle_message(self, key: Optional[str], payload: dict) -> None:
        # Payload expected: {"event":"user_verified","version":1,"user_id":...,"email":...,"occurred_at":...}
        user_id = payload.get("user_id")
        email = payload.get("email")
        if not user_id:
            logger.warning("user_verified message missing user_id")
            return

        # Upsert minimal profile or set services.email_verified = True
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(select(Profile).where(Profile.user_id == user_id))
                obj = result.scalar_one_or_none()
                if obj:
                    services = obj.services or {}
                    services["email_verified"] = True
                    obj.services = services
                    await session.flush()
                    await session.commit()
                    logger.info("profile_email_verified_updated", extra={"user_id": user_id})
                    return

                # create minimal profile
                new = Profile(user_id=user_id, display_name=email or "", email=email, services={"email_verified": True})
                session.add(new)
                await session.flush()
                await session.commit()
                logger.info("profile_created_on_user_verified", extra={"user_id": user_id})
            except Exception:
                await session.rollback()
                logger.exception("failed_upsert_profile_on_user_verified")


consumer = UserVerifiedConsumer()

async def start_consumer() -> None:
    await consumer.start()


async def stop_consumer() -> None:
    await consumer.stop()
