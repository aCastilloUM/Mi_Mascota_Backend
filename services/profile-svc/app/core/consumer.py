from __future__ import annotations

import asyncio
import logging
from typing import Optional

import orjson
from aiokafka import AIOKafkaConsumer
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

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

        # Subscribe to both user verified and user registered topics so we can
        # create a richer profile at registration time (full name + email)
        self._consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPIC_USER_VERIFIED,
            "user.registered.v1",
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
        # We support both:
        # - user_registered (published by auth-svc at registration)
        #   payload example: {"event":"user_registered","payload": {"user_id":..., "email":..., "full_name": ...}, ...}
        # - user_verified (published when email is verified)
        #   payload example: {"event":"user_verified","user_id":..., "email": ..., "occurred_at":...}

        event = payload.get("event")

        if event == "user_registered":
            data = payload.get("payload") or {}
            user_id = data.get("user_id")
            email = data.get("email")
            full_name = data.get("full_name") or ""
            if not user_id:
                logger.warning("user_registered message missing user_id")
                return

            async with AsyncSessionLocal() as session:
                try:
                    # if profile exists by user_id, update email/display_name
                    res = await session.execute(select(Profile).where(Profile.user_id == user_id))
                    obj = res.scalar_one_or_none()
                    if obj:
                        obj.display_name = full_name or (obj.display_name or email)
                        obj.email = email or obj.email
                        await session.flush()
                        await session.commit()
                        logger.info("profile_updated_on_user_registered", extra={"user_id": user_id})
                        return

                    # try to create profile using provided full_name and email
                    new = Profile(user_id=user_id, display_name=full_name or (email or ""), email=email, services={})
                    session.add(new)
                    try:
                        await session.flush()
                        await session.commit()
                        logger.info("profile_created_on_user_registered", extra={"user_id": user_id})
                        return
                    except IntegrityError:
                        # Unique constraint (email/user_id) — try to update existing by email
                        await session.rollback()
                        try:
                            r2 = await session.execute(select(Profile).where(Profile.email == email))
                            existing = r2.scalar_one_or_none()
                            if existing:
                                existing.user_id = existing.user_id or user_id
                                existing.display_name = existing.display_name or full_name
                                sv = existing.services or {}
                                existing.services = sv
                                await session.flush()
                                await session.commit()
                                logger.info("profile_upserted_on_user_registered_by_email", extra={"email": email, "user_id": user_id})
                                return
                        except Exception:
                            await session.rollback()
                            logger.exception("failed_handle_integrity_error_on_user_registered")
                except Exception:
                    await session.rollback()
                    logger.exception("failed_handle_user_registered_message")
            return

        if event == "user_verified":
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

                    # try to get full_name from auth.users table in same DB if available
                    full_name = None
                    try:
                        r = await session.execute(text("SELECT full_name FROM auth.users WHERE id = :id LIMIT 1"), {"id": user_id})
                        full_name = r.scalar_one_or_none()
                    except Exception:
                        # ignore if cross-schema/table not accessible
                        full_name = None

                    # create minimal profile (prefer full_name when available)
                    new = Profile(user_id=user_id, display_name=full_name or email or "", email=email, services={"email_verified": True})
                    session.add(new)
                    try:
                        await session.flush()
                        await session.commit()
                        logger.info("profile_created_on_user_verified", extra={"user_id": user_id})
                    except IntegrityError:
                        # Handle race / unique constraint (email already exists for another profile)
                        await session.rollback()
                        logger.warning("IntegrityError on insert — attempting to upsert by email", extra={"email": email, "user_id": user_id})
                        try:
                            res = await session.execute(select(Profile).where(Profile.email == email))
                            existing = res.scalar_one_or_none()
                            if existing:
                                sv = existing.services or {}
                                sv["email_verified"] = True
                                existing.services = sv
                                await session.flush()
                                await session.commit()
                                logger.info("profile_email_verified_updated_by_email", extra={"email": email, "user_id": user_id})
                                return
                            else:
                                logger.error("IntegrityError but no existing profile found by email", extra={"email": email})
                        except Exception:
                            await session.rollback()
                            logger.exception("failed_handle_integrity_error_on_upsert")
                except Exception:
                    await session.rollback()
                    logger.exception("failed_upsert_profile_on_user_verified")
            return

        # Unknown event — log and ignore
        logger.debug("consumer_received_unknown_event", extra={"event": event, "payload": payload})


consumer = UserVerifiedConsumer()

async def start_consumer() -> None:
    await consumer.start()


async def stop_consumer() -> None:
    await consumer.stop()
