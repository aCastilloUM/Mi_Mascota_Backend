import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi_pagination import add_pagination

from app.core.config import settings
from app.core.kafka import get_producer, stop_producer
from app.core.consumer import start_consumer, stop_consumer
from app.core.logging import setup_logging
from app.routers import health, profiles
from app.db.bootstrap import ensure_schema

setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ensure_schema(settings.DB_SCHEMA)
    except Exception:
        logger.exception("Failed to ensure database schema")

    if settings.KAFKA_ENABLED:
        try:
            await get_producer()
            try:
                await start_consumer()
            except Exception:
                logger.exception("Kafka consumer start failed")
        except Exception:
            logger.exception("Kafka producer start failed")
    else:
        logger.info("Kafka disabled; skipping producer startup")

    try:
        yield
    finally:
        if settings.KAFKA_ENABLED:
            try:
                await stop_producer()
            except Exception:
                logger.exception("Kafka producer stop failed")
            try:
                await stop_consumer()
            except Exception:
                logger.exception("Kafka consumer stop failed")
        else:
            logger.debug("Kafka disabled; no producer to stop")


app = FastAPI(
    title=settings.APP_NAME,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(health.router)
app.include_router(profiles.router)
add_pagination(app)
