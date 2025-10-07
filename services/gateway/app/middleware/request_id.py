"""
Middleware de Request-ID para el Gateway.
Genera o extrae Request-ID y lo propaga a todos los servicios backend.
"""
import uuid
import time
import logging
from fastapi import Request

logger = logging.getLogger("gateway")


async def request_id_middleware(request: Request, call_next):
    """
    Middleware que:
    1. Genera o extrae Request-ID
    2. Lo inyecta en request.state para uso interno
    3. Lo propaga en response headers
    4. Logea el acceso con duración y detalles
    """
    # Generar o extraer Request-ID
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Cliente info
    client_ip = request.client.host if request.client else "unknown"
    
    # Log de inicio
    start_time = time.time()
    
    logger.info(
        "request_start",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": client_ip,
        }
    )
    
    # Procesar request
    status_code = 500  # default
    try:
        response = await call_next(request)
        status_code = response.status_code
        
        # Inyectar Request-ID en response
        response.headers["X-Request-Id"] = request_id
        
        return response
        
    finally:
        # Log de finalización
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            }
        )
