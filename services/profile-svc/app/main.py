import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi_pagination import add_pagination

from app.core.config import settings
from app.core.kafka import get_producer, stop_producer
from app.core.consumer import start_consumer, stop_consumer
from app.core.logging import setup_logging
from app.routers import health, profiles
from app.routers import internal as internal_router
from app.db.bootstrap import ensure_schema
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

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

# Expose Prometheus metrics at /metrics
try:
    Instrumentator().instrument(app).expose(app, include_in_schema=False, endpoint="/metrics")
except Exception:
    logger.exception("prometheus_instrumentation_failed")

# Support HEAD on /metrics so browsers or tools issuing HEAD receive proper headers
@app.head("/metrics")
async def metrics_head():
    try:
        data = generate_latest()
        headers = {
            "content-type": CONTENT_TYPE_LATEST,
            "content-length": str(len(data)),
        }
        return Response(content=b"", media_type=CONTENT_TYPE_LATEST, headers=headers)
    except Exception:
        logger.exception("metrics_head_failed")
        return Response(status_code=500)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(health.router)
app.include_router(profiles.router)
app.include_router(internal_router.router)
add_pagination(app)
