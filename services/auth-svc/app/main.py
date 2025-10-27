# services/auth-svc/app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import uuid
import time

from app.core.config import settings
from app.core.logging import setup_logging, client_ip_from_scope
from app.api.v1 import auth
from app.api.v1 import email_verification
from app.api.v1 import password_reset
from app.api.v1 import password_change
from app.api.v1 import two_factor
from app.api.health import router as ops_router
from app.events.kafka import bus
from app.infra.redis import redis_client

setup_logging()
logger = logging.getLogger("auth-svc")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Se ejecuta al iniciar
    logger.info("service_start", extra={"db": settings.database_url})
    
    # Redis
    try:
        await redis_client.start()
    except Exception:
        logger.exception("redis_start_failed")
    
    # Inicia productor Kafka
    try:
        await bus.start()
    except Exception:
        logger.exception("kafka_start_failed")
        # En dev podés seguir sin Kafka; en prod quizá quieras fallar
    
    yield
    
    # Se ejecuta al cerrar
    try:
        await bus.stop()
    except Exception:
        logger.exception("kafka_stop_failed")
    
    try:
        await redis_client.stop()
    except Exception:
        logger.exception("redis_stop_failed")
    
    logger.info("service_stop")

app = FastAPI(title="auth-svc", lifespan=lifespan)

# --- CORS: habilitar en dev cuando el frontend llama directamente al servicio ---
# El gateway suele encargarse de CORS en despliegues con proxy, pero en
# desarrollo (cuando el frontend tests/vite llama a auth-svc en localhost:8080)
# necesitamos permitir el origen del frontend y enviar credenciales.
try:
    origins = []
    if settings.cors_allowed_origins:
        origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
    elif settings.frontend_url:
        origins = [settings.frontend_url]

    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=[m.strip() for m in (settings.cors_allowed_methods or "*").split(",") if m.strip()] or ["*"],
            allow_headers=[h.strip() for h in (settings.cors_allowed_headers or "*").split(",") if h.strip()] or ["*"],
        )
        logger.info("cors_configured", extra={"origins": origins})
except Exception:
    logger.exception("cors_configuration_failed")

# --- Request-Id + access log ---
@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    """
    Agrega Request-Id a cada request/response y logea el acceso.
    REUTILIZA el Request-ID del gateway si existe, si no genera uno nuevo.
    """
    # Reutilizar Request-ID del gateway (propagado en header)
    rid = request.headers.get(settings.request_id_header) or str(uuid.uuid4())
    request.state.request_id = rid

    start = time.perf_counter()
    status_code = 500  # default si hay error
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers[settings.request_id_header] = rid
        return response
    finally:
        dur_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "access",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": status_code,
                "duration_ms": dur_ms,
                "request_id": rid,
                "client_ip": client_ip_from_scope(request.scope),
            },
        )

# Rutas ops (health/ready)
app.include_router(ops_router)

# Rutas v1 (auth endpoints)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(email_verification.router, prefix="/api/v1")
app.include_router(password_reset.router, prefix="/api/v1")
app.include_router(password_change.router, prefix="/api/v1")
app.include_router(two_factor.router, prefix="/api/v1")

# Health extra simple (opcional)
@app.get("/healthz")
async def healthz():
    return {"ok": True}


