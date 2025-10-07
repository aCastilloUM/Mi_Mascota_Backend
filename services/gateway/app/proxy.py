"""
Proxy para reenviar requests a los microservicios backend.
"""
import httpx  # type: ignore
import logging
import time
from fastapi import Request, HTTPException
from fastapi.responses import Response
from app.middleware.circuit_breaker import get_circuit_breaker
from app.middleware.metrics import record_backend_request, record_backend_error

logger = logging.getLogger(__name__)


async def proxy_request(
    request: Request,
    target_url: str,
    path: str = None,
    timeout: float = 30.0,
    service_name: str = "backend"
) -> Response:
    """
    Proxy HTTP que reenvía el request al servicio backend.
    
    Incluye:
    - Circuit Breaker para prevenir cascada de fallos
    - Métricas de Prometheus para observabilidad
    - Propagación de headers (Request-ID, User-ID, etc.)
    
    Args:
        request: Request original de FastAPI
        target_url: URL base del servicio backend (ej: http://localhost:8002)
        path: Path específico (opcional, por defecto usa el path del request)
        timeout: Timeout en segundos
        service_name: Nombre del servicio backend (para circuit breaker y metrics)
    
    Returns:
        Response del servicio backend
    """
    if path is None:
        path = request.url.path
    
    # Construir URL completa
    full_url = f"{target_url}{path}"
    if request.url.query:
        full_url = f"{full_url}?{request.url.query}"
    
    # Headers a reenviar
    headers = dict(request.headers)
    
    # Remover headers que no deben reenviarse
    headers.pop("host", None)
    
    # Propagar Request-ID del gateway a backends
    if hasattr(request.state, "request_id"):
        headers["X-Request-Id"] = request.state.request_id
    
    # Agregar headers de usuario autenticado (si existe)
    if hasattr(request.state, "user_id"):
        headers["X-User-ID"] = request.state.user_id
        
        # Si hay más info del token, agregarla
        if hasattr(request.state, "token_payload"):
            payload = request.state.token_payload
            # Puedes agregar más campos según necesites
            if "email" in payload:
                headers["X-User-Email"] = payload["email"]
    
    # Leer body del request
    body = await request.body()
    
    # Obtener Circuit Breaker para este servicio
    circuit_breaker = get_circuit_breaker(service_name)
    
    # Función interna que hace el request real
    async def _do_request():
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                logger.info(f"Proxying {request.method} {full_url}")
                
                # Hacer request al servicio backend
                backend_response = await client.request(
                    method=request.method,
                    url=full_url,
                    headers=headers,
                    content=body,
                    cookies=request.cookies,
                )
                
                # Registrar métricas
                duration = time.time() - start_time
                record_backend_request(service_name, backend_response.status_code, duration)
                
                # Construir response para el cliente
                response = Response(
                    content=backend_response.content,
                    status_code=backend_response.status_code,
                    headers=dict(backend_response.headers),
                )
                
                return response
                
        except httpx.TimeoutException as e:
            duration = time.time() - start_time
            record_backend_request(service_name, 504, duration)
            record_backend_error(service_name, "TimeoutException")
            
            logger.error(f"Timeout llamando a {full_url}")
            raise HTTPException(
                status_code=504,
                detail={"code": "GATEWAY_TIMEOUT", "message": "El servicio backend no respondió a tiempo"}
            )
        except httpx.RequestError as e:
            duration = time.time() - start_time
            record_backend_request(service_name, 503, duration)
            record_backend_error(service_name, "RequestError")
            
            logger.error(f"Error conectando a {full_url}: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail={"code": "SERVICE_UNAVAILABLE", "message": f"Servicio no disponible: {str(e)}"}
            )
        except Exception as e:
            duration = time.time() - start_time
            record_backend_request(service_name, 500, duration)
            record_backend_error(service_name, type(e).__name__)
            
            logger.exception(f"Error inesperado en proxy: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={"code": "INTERNAL_ERROR", "message": "Error interno del gateway"}
            )
    
    # Ejecutar request con Circuit Breaker
    try:
        return await circuit_breaker.call_async(_do_request)
    except HTTPException:
        # Re-raise HTTPException sin envolver
        raise
    except Exception as e:
        # Circuit breaker lanzó excepción (probablemente 503)
        raise
