"""
Rutas del Gateway - Enruta requests a los microservicios correspondientes.
"""
from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.config import settings
from app.proxy import proxy_request

router = APIRouter()


# ============= AUTH SERVICE =============
@router.api_route("/api/v1/auth/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def auth_service(path: str, request: Request) -> Response:
    """Proxy para el servicio de autenticación."""
    return await proxy_request(
        request,
        settings.auth_service_url,
        path=f"/api/v1/auth/{path}",
        service_name="auth-svc"
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
