# services/auth-svc/app/api/v1/email_verification.py
"""
Endpoints para Email Verification
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.db.repositories import UserRepo
from app.services.auth_service import AuthService, EmailVerificationError
from app.api.v1.schemas_email import (
    VerifyEmailRequest,
    ResendVerificationRequest,
    EmailVerificationResponse,
)

router = APIRouter(prefix="/auth", tags=["Email Verification"])


@router.post("/verify-email", response_model=EmailVerificationResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Verifica el email del usuario con el token recibido por email.
    
    - **token**: Token de verificación recibido por email
    """
    users = UserRepo(session)
    svc = AuthService(users=users)
    
    try:
        await svc.verify_email(payload.token)
        return EmailVerificationResponse(
            message="Email verificado exitosamente",
            email_verified=True
        )
    except EmailVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resend-verification", response_model=EmailVerificationResponse)
async def resend_verification(
    payload: ResendVerificationRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Reenvía el email de verificación al usuario.
    
    - **email**: Email del usuario
    """
    users = UserRepo(session)
    svc = AuthService(users=users)
    
    try:
        await svc.resend_verification_email(payload.email)
        return EmailVerificationResponse(
            message="Email de verificación reenviado exitosamente",
            email_verified=False
        )
    except EmailVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
