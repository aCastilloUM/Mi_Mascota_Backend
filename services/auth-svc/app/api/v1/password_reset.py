# services/auth-svc/app/api/v1/password_reset.py
"""
Endpoints para Password Reset
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.db.repositories import UserRepo
from app.services.auth_service import AuthService, PasswordResetError
from app.api.v1.schemas_email import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    PasswordResetResponse,
)

router = APIRouter(prefix="/auth", tags=["Password Reset"])


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Solicita un reset de contraseña. Envía un email con el token de reset.
    
    - **email**: Email del usuario
    
    Por seguridad, siempre retorna éxito incluso si el email no existe.
    """
    users = UserRepo(session)
    svc = AuthService(users=users)
    
    await svc.request_password_reset(payload.email)
    return PasswordResetResponse(
        message="Si el email existe, recibirás un enlace para resetear tu contraseña"
    )


@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Resetea la contraseña con el token recibido por email.
    
    - **token**: Token de reset recibido por email
    - **new_password**: Nueva contraseña (mínimo 8 caracteres)
    """
    users = UserRepo(session)
    svc = AuthService(users=users)
    
    try:
        await svc.reset_password(payload.token, payload.new_password)
        return PasswordResetResponse(
            message="Contraseña actualizada exitosamente"
        )
    except PasswordResetError as e:
        raise HTTPException(status_code=400, detail=str(e))
