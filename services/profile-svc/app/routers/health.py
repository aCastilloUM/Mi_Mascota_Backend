from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest, ProcessCollector, PlatformCollector

router = APIRouter(prefix= '/health', tags=["health"])


@router.get("")
async def health():
    return {"status": "ok"}


@router.get("/metrics")
async def metrics():
    # Exposición básica de métricas de proceso (Prometheus)
    registry = CollectorRegistry()
    ProcessCollector(registry=registry)
    PlatformCollector(registry=registry)
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
