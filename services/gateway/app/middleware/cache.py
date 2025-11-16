# services/gateway/app/middleware/cache.py
"""
Response Caching Middleware
Cachea responses de GET requests en Redis para reducir latencia
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import hashlib
import json
import logging
from typing import Optional
import redis.asyncio as redis  # type: ignore

logger = logging.getLogger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware de cache para responses
    
    - Solo cachea GET requests
    - Usa Redis como backend
    - Cache key: hash(method + path + query_params + headers relevantes)
    - TTL configurable por ruta
    """
    
    def __init__(self, app, redis_url: str, default_ttl: int = 60):
        super().__init__(app)
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.redis_client: Optional[redis.Redis] = None
        
        # Configuración de TTL por prefijo de ruta
        self.ttl_config = {
            "/api/v1/auth/me": 300,      # 5 minutos - info de usuario
            "/health": 10,                # 10 segundos - health checks
            "/ready": 10,                 # 10 segundos
        }
        
        # Rutas que NO se cachean
        self.no_cache_paths = {
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/logout",
            "/api/v1/auth/refresh",
            "/api/v1/auth/verify-email",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/change-password",
            "/metrics",
        }
    
    async def dispatch(self, request: Request, call_next):
        # Solo cachear GET requests
        if request.method != "GET":
            return await call_next(request)
        
        # Verificar si la ruta está en no-cache
        if request.url.path in self.no_cache_paths:
            return await call_next(request)
        
        # Conectar a Redis si no está conectado
        if self.redis_client is None:
            try:
                self.redis_client = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                logger.error(f"cache_redis_connection_failed", extra={"error": str(e)})
                # Si Redis falla, pasar sin cache
                return await call_next(request)
        
        # Generar cache key
        cache_key = self._generate_cache_key(request)
        
        # Intentar obtener de cache
        try:
            cached = await self.redis_client.get(cache_key)
            if cached:
                logger.info(
                    "cache_hit",
                    extra={
                        "path": request.url.path,
                        "cache_key": cache_key[:20] + "..."
                    }
                )
                
                # Parsear cached response
                cached_data = json.loads(cached)
                return JSONResponse(
                    content=cached_data["body"],
                    status_code=cached_data["status_code"],
                    headers={
                        **{k: v for k, v in (cached_data.get("headers", {}) or {}).items() if k.lower() != 'content-length'},
                        "X-Cache": "HIT"
                    }
                )
        except Exception as e:
            logger.warning(f"cache_get_failed", extra={"error": str(e)})
        
        # Cache miss - ejecutar request
        logger.info(
            "cache_miss",
            extra={
                "path": request.url.path,
                "cache_key": cache_key[:20] + "..."
            }
        )
        
        response = await call_next(request)
        
        # Solo cachear responses exitosas (2xx)
        if 200 <= response.status_code < 300:
            try:
                # Leer el body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                # Parsear body
                try:
                    body_json = json.loads(body.decode())
                except:
                    body_json = body.decode()
                
                # Guardar en cache
                cache_data = {
                    "body": body_json,
                    "status_code": response.status_code,
                    "headers": dict(response.headers)
                }
                
                ttl = self._get_ttl(request.url.path)
                await self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(cache_data)
                )
                
                logger.info(
                    "cache_set",
                    extra={
                        "path": request.url.path,
                        "ttl": ttl,
                        "cache_key": cache_key[:20] + "..."
                    }
                )
                
                # Retornar response con body reconstruido
                new_headers = {k: v for k, v in dict(response.headers).items() if k.lower() != 'content-length'}
                new_headers.update({"X-Cache": "MISS"})
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=new_headers,
                    media_type=response.media_type
                )
                
            except Exception as e:
                logger.error(f"cache_set_failed", extra={"error": str(e)})
        
        # Si algo falla, retornar response original
        return response
    
    def _generate_cache_key(self, request: Request) -> str:
        """
        Genera una cache key única basada en request
        
        Incluye: method, path, query_params, user_id (si existe)
        """
        key_parts = [
            request.method,
            request.url.path,
            str(sorted(request.query_params.items())),
        ]
        
        # Incluir user_id si existe (para cache por usuario)
        user_id = request.headers.get("x-user-id")
        if user_id:
            key_parts.append(f"user:{user_id}")
        
        key_string = "|".join(key_parts)
        
        # Hash para key más corta
        return f"gateway:cache:{hashlib.sha256(key_string.encode()).hexdigest()}"
    
    def _get_ttl(self, path: str) -> int:
        """Obtiene el TTL configurado para una ruta"""
        for prefix, ttl in self.ttl_config.items():
            if path.startswith(prefix):
                return ttl
        return self.default_ttl
    
    async def clear_cache(self, pattern: str = "gateway:cache:*"):
        """Limpia el cache (útil para invalidación manual)"""
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.info(f"cache_cleared", extra={"keys_deleted": len(keys)})
            except Exception as e:
                logger.error(f"cache_clear_failed", extra={"error": str(e)})


# Instancia global (se inicializa en main.py)
cache_middleware: Optional[CacheMiddleware] = None


def get_cache_middleware() -> Optional[CacheMiddleware]:
    """Obtiene la instancia global de cache middleware"""
    return cache_middleware
