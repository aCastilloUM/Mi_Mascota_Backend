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


# ============= OTROS SERVICIOS =============
# Cuando implementes otros servicios (mascotas, veterinarios, etc.),
# agrégalos aquí siguiendo el mismo patrón:
#
# @router.api_route("/api/v1/servicio/{path:path}", methods=[...])
# async def servicio(path: str, request: Request) -> Response:
#     return await proxy_request(
#         request,
#         settings.servicio_url,
#         path=f"/api/v1/servicio/{path}"
#     )
