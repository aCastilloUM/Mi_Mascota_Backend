"""
Rutas del Gateway - Enruta requests a los microservicios correspondientes.
"""
from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.config import settings
from app.proxy import proxy_request

router = APIRouter()


# ============= AUTH SERVICE =============
@router.api_route("/api/v1/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def auth_service(path: str, request: Request) -> Response:
    """Proxy para el servicio de autenticación."""
    return await proxy_request(
        request,
        settings.auth_service_url,
        path=f"/api/v1/auth/{path}",
        service_name="auth-svc"
    )


# Backwards-compatible proxy: some frontend calls use /api/v1/2fa/* (missing 'auth' segment)
# Add explicit routes that forward /api/v1/2fa/... to the auth service under /api/v1/auth/2fa/...
@router.api_route("/api/v1/2fa", methods=["POST", "OPTIONS"])
async def twofa_root(request: Request) -> Response:
    """Compat proxy for /api/v1/2fa -> /api/v1/auth/2fa"""
    return await proxy_request(
        request,
        settings.auth_service_url,
        path=f"/api/v1/auth/2fa",
        service_name="auth-svc",
    )


@router.api_route("/api/v1/2fa/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def twofa_service(path: str, request: Request) -> Response:
    """Compat proxy for /api/v1/2fa/{path} -> /api/v1/auth/2fa/{path}"""
    return await proxy_request(
        request,
        settings.auth_service_url,
        path=f"/api/v1/auth/2fa/{path}",
        service_name="auth-svc",
    )


# ============= PROFILE SERVICE =============
@router.api_route("/api/v1/profiles", methods=["GET", "POST", "OPTIONS"])
async def profiles_root(request: Request) -> Response:
    """Proxy para la colección de perfiles."""
    return await proxy_request(
        request,
        settings.profile_service_url,
        path="/profiles",
        service_name="profiles-svc",
    )


@router.api_route("/api/v1/profiles/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def profiles_service(path: str, request: Request) -> Response:
    """Proxy para operaciones sobre un perfil."""
    return await proxy_request(
        request,
        settings.profile_service_url,
        path=f"/profiles/{path}",
        service_name="profiles-svc",
    )
