"""
API Gateway - Punto de entrada único para todos los microservicios.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.core.logging import setup_logging
from app.middleware.request_id import request_id_middleware
from app.middleware.rate_limit import rate_limit_middleware
from app.middleware.auth import auth_middleware
from app.middleware.cache import CacheMiddleware
from app.middleware.metrics import MetricsMiddleware, metrics_endpoint
from app.middleware.circuit_breaker import get_all_circuit_breakers
from app.routes import proxy_routes

# Configurar logging estructurado
setup_logging()
logger = logging.getLogger("gateway")

# Crear app
app = FastAPI(
    title="API Gateway - Mi Mascota",
    description="Gateway que enruta requests a los microservicios del sistema",
    version="1.0.0"
)

# --- CORS (primero) ---
origins = settings.cors_origins.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Metrics (primero para capturar todo) ---
app.add_middleware(MetricsMiddleware)

# --- Cache (antes de request processing) ---
app.add_middleware(
    CacheMiddleware,
    redis_url=getattr(settings, 'redis_url', 'redis://localhost:6379/0'),
    default_ttl=60
)

# --- Request-ID (genera/propaga) ---
app.middleware("http")(request_id_middleware)

# --- Rate Limiting Global (protección anti-spam) ---
app.middleware("http")(rate_limit_middleware)

# --- Autenticación (valida JWT) ---
app.middleware("http")(auth_middleware)

# Incluir rutas de proxy
app.include_router(proxy_routes.router)


# ==================== ENDPOINTS ====================

# Prometheus Metrics
@app.get("/metrics")
async def get_metrics(request: Request):
    """
    Endpoint para Prometheus.
    
    Expone métricas en formato Prometheus:
    - gateway_http_requests_total
    - gateway_http_request_duration_seconds
    - gateway_backend_requests_total
    - gateway_circuit_breaker_state
    - gateway_cache_hits_total
    - etc.
    """
    return await metrics_endpoint(request)


# Circuit Breaker Status
@app.get("/circuit-breakers")
async def circuit_breakers_status():
    """
    Estado de todos los circuit breakers.
    
    Útil para debugging y monitoreo.
    """
    return {
        "circuit_breakers": get_all_circuit_breakers()
    }


# Health check del gateway
@app.get("/health")
async def health():
    """Health check del gateway."""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Información del gateway."""
    return {
        "service": "API Gateway - Mi Mascota",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
        "circuit_breakers": "/circuit-breakers"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.gateway_port,
        reload=True
    )

