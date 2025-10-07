# services/gateway/app/middleware/metrics.py
"""
Prometheus Metrics Middleware
Exporta métricas de requests, latencia, errores, etc.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST  # type: ignore
from starlette.responses import Response
import time
import logging

logger = logging.getLogger(__name__)


# ==================== MÉTRICAS ====================

# Contador de requests por método, path y status
http_requests_total = Counter(
    'gateway_http_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status_code']
)

# Histograma de latencia de requests
http_request_duration_seconds = Histogram(
    'gateway_http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'path'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Gauge de requests en progreso
http_requests_in_progress = Gauge(
    'gateway_http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'path']
)

# Contador de errores por tipo
http_errors_total = Counter(
    'gateway_http_errors_total',
    'Total HTTP errors',
    ['method', 'path', 'error_type']
)

# Métricas de backend
backend_requests_total = Counter(
    'gateway_backend_requests_total',
    'Total requests to backend services',
    ['service', 'status_code']
)

backend_request_duration_seconds = Histogram(
    'gateway_backend_request_duration_seconds',
    'Backend request latency',
    ['service'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

backend_errors_total = Counter(
    'gateway_backend_errors_total',
    'Total backend errors',
    ['service', 'error_type']
)

# Circuit Breaker metrics
circuit_breaker_state = Gauge(
    'gateway_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['service']
)

circuit_breaker_failures = Counter(
    'gateway_circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['service']
)

# Cache metrics
cache_hits_total = Counter(
    'gateway_cache_hits_total',
    'Total cache hits',
    ['path']
)

cache_misses_total = Counter(
    'gateway_cache_misses_total',
    'Total cache misses',
    ['path']
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware que registra métricas de Prometheus
    """
    
    async def dispatch(self, request: Request, call_next):
        # No registrar métricas del endpoint de métricas mismo
        if request.url.path == "/metrics":
            return await call_next(request)
        
        method = request.method
        path = request.url.path
        
        # Normalizar path para evitar cardinalidad alta
        # (eliminar IDs, UUIDs, etc.)
        normalized_path = self._normalize_path(path)
        
        # Incrementar gauge de requests en progreso
        http_requests_in_progress.labels(method=method, path=normalized_path).inc()
        
        start_time = time.time()
        status_code = 500  # Default si hay error
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        
        except Exception as e:
            # Registrar error
            error_type = type(e).__name__
            http_errors_total.labels(
                method=method,
                path=normalized_path,
                error_type=error_type
            ).inc()
            
            logger.error(
                "metrics_request_error",
                extra={
                    "method": method,
                    "path": path,
                    "error": str(e),
                    "error_type": error_type
                }
            )
            raise
        
        finally:
            # Registrar duración
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                path=normalized_path
            ).observe(duration)
            
            # Decrementar gauge de requests en progreso
            http_requests_in_progress.labels(method=method, path=normalized_path).dec()
            
            # Incrementar contador de requests
            http_requests_total.labels(
                method=method,
                path=normalized_path,
                status_code=status_code
            ).inc()
    
    def _normalize_path(self, path: str) -> str:
        """
        Normaliza paths para reducir cardinalidad
        
        Ejemplos:
        - /api/v1/users/123 -> /api/v1/users/{id}
        - /api/v1/auth/verify-email -> /api/v1/auth/verify-email
        """
        # Rutas conocidas (no normalizar)
        known_paths = {
            "/health",
            "/ready",
            "/metrics",
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/logout",
            "/api/v1/auth/refresh",
            "/api/v1/auth/me",
            "/api/v1/auth/verify-email",
            "/api/v1/auth/resend-verification",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/change-password",
        }
        
        if path in known_paths:
            return path
        
        # Reemplazar UUIDs y números por placeholders
        import re
        
        # UUID pattern
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{id}',
            path,
            flags=re.IGNORECASE
        )
        
        # Números largos (probablemente IDs)
        path = re.sub(r'/\d{3,}', '/{id}', path)
        
        return path


def record_backend_request(service: str, status_code: int, duration: float):
    """Registra una request a un backend"""
    backend_requests_total.labels(service=service, status_code=status_code).inc()
    backend_request_duration_seconds.labels(service=service).observe(duration)


def record_backend_error(service: str, error_type: str):
    """Registra un error de backend"""
    backend_errors_total.labels(service=service, error_type=error_type).inc()


def record_circuit_breaker_state(service: str, state: str):
    """
    Registra estado de circuit breaker
    
    state: 'closed', 'open', 'half_open'
    """
    state_value = {
        'closed': 0,
        'open': 1,
        'half_open': 2
    }.get(state, 0)
    
    circuit_breaker_state.labels(service=service).set(state_value)


def record_circuit_breaker_failure(service: str):
    """Registra un fallo de circuit breaker"""
    circuit_breaker_failures.labels(service=service).inc()


def record_cache_hit(path: str):
    """Registra un cache hit"""
    cache_hits_total.labels(path=path).inc()


def record_cache_miss(path: str):
    """Registra un cache miss"""
    cache_misses_total.labels(path=path).inc()


async def metrics_endpoint(request: Request) -> Response:
    """
    Endpoint para exponer métricas en formato Prometheus
    
    GET /metrics
    """
    metrics_data = generate_latest()
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
