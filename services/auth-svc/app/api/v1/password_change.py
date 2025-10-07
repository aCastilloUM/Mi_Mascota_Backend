# services/auth-svc/app/api/v1/password_change.py
"""
Endpoint para Change Password (usuario autenticado)
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.deps import get_session
from app.db.repositories import UserRepo
from app.services.auth_service import AuthService
from app.api.v1.schemas_email import (
    ChangePasswordRequest,
    ChangePasswordResponse,
)

router = APIRouter(prefix="/auth", tags=["Password Management"])


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    payload: ChangePasswordRequest,
    session: AsyncSession = Depends(get_session),
    x_user_id: str = Header(..., description="User ID desde el Gateway"),
):
    """
    Cambia la contraseña del usuario autenticado.
    
    - **old_password**: Contraseña actual
    - **new_password**: Nueva contraseña (mínimo 8 caracteres)
    
    Requiere autenticación (header X-User-ID desde Gateway).
    """
    users = UserRepo(session)
    svc = AuthService(users=users)
    
    try:
        user_id = UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="User ID inválido")
    
    try:
        await svc.change_password(user_id, payload.old_password, payload.new_password)
        return ChangePasswordResponse(
            message="Contraseña actualizada exitosamente"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al cambiar contraseña")
