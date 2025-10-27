"""
Middleware de autenticación para el Gateway.
Valida el JWT y agrega información del usuario en los headers.
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import jwt
import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Rutas públicas que NO requieren autenticación
PUBLIC_PATHS = [
    "/health",
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    # Make verify-email public so users can verify from the frontend link
    "/api/v1/auth/verify-email",
]


def decode_token(token: str) -> dict:
    """Decodifica y valida un JWT."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "iss", "sub", "aud"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"code": "TOKEN_EXPIRED", "message": "Token expirado"})
    except jwt.InvalidTokenError as e:
        logger.warning(f"Token inválido: {str(e)}")
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN", "message": "Token inválido"})


def extract_token_from_header(authorization: Optional[str]) -> Optional[str]:
    """Extrae el token del header Authorization."""
    if not authorization:
        return None
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    
    return parts[1]


def is_public_path(path: str) -> bool:
    """Verifica si la ruta es pública."""
    for public_path in PUBLIC_PATHS:
        if path.startswith(public_path):
            return True
    return False


async def auth_middleware(request: Request, call_next):
    """
    Middleware que valida JWT en rutas protegidas.
    Agrega headers X-User-ID y X-User-Email para los servicios backend.
    """
    path = request.url.path
    # Allow preflight requests to pass through without authentication so CORS
    # handling (CORSMiddleware) can respond correctly. Browsers send OPTIONS
    # preflight requests without Authorization headers.
    if request.method == "OPTIONS":
        return await call_next(request)
    
    # Rutas públicas: no requieren autenticación
    if is_public_path(path):
        return await call_next(request)
    
    # Rutas protegidas: validar token
    authorization = request.headers.get("authorization")
    token = extract_token_from_header(authorization)
    
    if not token:
        return JSONResponse(
            status_code=401,
            content={"detail": {"code": "MISSING_TOKEN", "message": "Token no proporcionado"}}
        )
    
    try:
        # Validar y decodificar token
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        # Agregar información del usuario en el request state
        # Esto estará disponible para las rutas y para el proxy
        request.state.user_id = user_id
        request.state.token_payload = payload
        
        logger.info(f"Usuario autenticado: {user_id} - {path}")
        
        # Continuar con el request
        response = await call_next(request)
        return response
        
    except HTTPException as e:
        return JSONResponse(
            status_code=e.status_code,
            content=e.detail
        )
    except Exception as e:
        logger.exception(f"Error en auth middleware: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": {"code": "INTERNAL_ERROR", "message": "Error interno del servidor"}}
        )
