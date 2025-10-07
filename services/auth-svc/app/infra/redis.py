# app/infra/redis.py
import asyncio
import logging
from typing import Optional
from redis.asyncio import Redis
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self) -> None:
        self._redis: Optional[Redis] = None
        self._lock = asyncio.Lock()

    async def start(self):
        async with self._lock:
            if self._redis:
                return
            self._redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
            # ping inicial
            try:
                await self._redis.ping()
                logger.info("redis_connected", extra={"url": settings.redis_url})
            except Exception:
                logger.exception("redis_connect_failed")
                raise

    async def stop(self):
        async with self._lock:
            if self._redis:
                await self._redis.close()
                self._redis = None
                logger.info("redis_closed")

    @property
    def conn(self) -> Redis:
        if not self._redis:
            raise RuntimeError("Redis not started")
        return self._redis

redis_client = RedisClient()
