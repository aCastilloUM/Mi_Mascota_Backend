# services/auth-svc/app/api/v1/email_verification.py
"""
Endpoints para Email Verification
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from urllib.parse import quote_plus

from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.db.repositories import UserRepo
from app.services.auth_service import AuthService, EmailVerificationError
from app.api.v1.schemas_email import (
    VerifyEmailRequest,
    ResendVerificationRequest,
    EmailVerificationResponse,
)
import logging
import time
from prometheus_client import Histogram, Counter

logger = logging.getLogger("auth-svc")

# Metrics for email verification flows
verify_email_duration = Histogram(
    "auth_verify_email_duration_seconds",
    "Duration of auth verify-email handler",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
verify_email_total = Counter(
    "auth_verify_email_total",
    "Total number of verify-email attempts",
    # label: outcome -> success|failure
    labelnames=("outcome",),
)
resend_verification_duration = Histogram(
    "auth_resend_verification_duration_seconds",
    "Duration of resend-verification handler",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
resend_verification_total = Counter(
    "auth_resend_verification_total",
    "Total number of resend-verification attempts",
    labelnames=("outcome",),
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
    
    start = time.perf_counter()
    try:
        await svc.verify_email(payload.token)
        verify_email_total.labels(outcome="success").inc()
        return EmailVerificationResponse(
            message="Email verificado exitosamente",
            email_verified=True
        )
    except EmailVerificationError as e:
        verify_email_total.labels(outcome="failure").inc()
        logger.info("verify_email_failed", extra={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        dur = time.perf_counter() - start
        try:
            verify_email_duration.observe(dur)
        except Exception:
            logger.exception("failed_recording_verify_metric")


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
    
    start = time.perf_counter()
    try:
        await svc.resend_verification_email(payload.email)
        resend_verification_total.labels(outcome="success").inc()
        return EmailVerificationResponse(
            message="Email de verificación reenviado exitosamente",
            email_verified=False
        )
    except EmailVerificationError as e:
        resend_verification_total.labels(outcome="failure").inc()
        logger.info("resend_verification_failed", extra={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        dur = time.perf_counter() - start
        try:
            resend_verification_duration.observe(dur)
        except Exception:
            logger.exception("failed_recording_resend_metric")



@router.get("/verify-email")
async def verify_email_get(
    token: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Verifica el email usando un GET (útil para links desde emails).
    Verifica el token y redirige a la UI (frontend) con un flag `verified`.
    """
    if not token:
        raise HTTPException(status_code=400, detail="Token faltante")

    users = UserRepo(session)
    svc = AuthService(users=users)
    start = time.perf_counter()
    try:
        await svc.verify_email(token)
        verify_email_total.labels(outcome="success").inc()
        redirect_to = f"{settings.frontend_url.rstrip('/')}/verify-email?verified=1"
        return RedirectResponse(redirect_to)
    except EmailVerificationError as e:
        verify_email_total.labels(outcome="failure").inc()
        msg = quote_plus(str(e))
        logger.info("verify_email_get_failed", extra={"error": str(e)})
        redirect_to = f"{settings.frontend_url.rstrip('/')}/verify-email?verified=0&message={msg}"
        try:
            dur = time.perf_counter() - start
            verify_email_duration.observe(dur)
        except Exception:
            logger.exception("failed_recording_verify_metric_get")
        return RedirectResponse(redirect_to)
