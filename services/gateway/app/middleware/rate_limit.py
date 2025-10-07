"""
Middleware de Rate Limiting Global para el Gateway.
Limita el número de requests por IP en una ventana de tiempo.
"""
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("gateway.rate_limit")


class GlobalRateLimiter:
    """
    Rate limiter simple en memoria por IP.
    Para producción con múltiples instancias, usar Redis.
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Args:
            max_requests: Número máximo de requests permitidos
            window_seconds: Ventana de tiempo en segundos
        """
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def is_allowed(self, client_ip: str) -> bool:
        """
        Verifica si la IP puede hacer un request.
        
        Args:
            client_ip: IP del cliente
            
        Returns:
            True si está permitido, False si excedió el límite
        """
        async with self.lock:
            now = datetime.now()
            cutoff = now - self.window
            
            # Limpiar requests antiguos fuera de la ventana
            self.requests[client_ip] = [
                timestamp for timestamp in self.requests[client_ip]
                if timestamp > cutoff
            ]
            
            # Verificar límite
            if len(self.requests[client_ip]) >= self.max_requests:
                logger.warning(
                    "rate_limit_exceeded",
                    extra={
                        "client_ip": client_ip,
                        "requests_count": len(self.requests[client_ip]),
                        "max_requests": self.max_requests,
                        "window_seconds": self.window.total_seconds()
                    }
                )
                return False
            
            # Registrar request
            self.requests[client_ip].append(now)
            return True
    
    async def get_remaining(self, client_ip: str) -> int:
        """Obtiene el número de requests restantes para una IP."""
        async with self.lock:
            now = datetime.now()
            cutoff = now - self.window
            
            # Limpiar requests antiguos
            self.requests[client_ip] = [
                timestamp for timestamp in self.requests[client_ip]
                if timestamp > cutoff
            ]
            
            current_count = len(self.requests[client_ip])
            return max(0, self.max_requests - current_count)


# Instancia global del rate limiter
# Configuración: 100 requests por minuto por IP
limiter = GlobalRateLimiter(max_requests=100, window_seconds=60)


async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware que aplica rate limiting global por IP.
    Rutas públicas como /health están exentas.
    """
    # Rutas exentas de rate limiting
    exempt_paths = ["/health", "/metrics"]
    if request.url.path in exempt_paths:
        return await call_next(request)
    
    # Obtener IP del cliente
    client_ip = request.client.host if request.client else "unknown"
    
    # Verificar rate limit
    if not await limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={
                "detail": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Demasiados requests. Por favor intenta más tarde."
                }
            },
            headers={
                "Retry-After": "60"  # Esperar 60 segundos
            }
        )
    
    # Obtener requests restantes
    remaining = await limiter.get_remaining(client_ip)
    
    # Procesar request
    response = await call_next(request)
    
    # Agregar headers informativos
    response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Window"] = f"{limiter.window.total_seconds()}s"
    
    return response
