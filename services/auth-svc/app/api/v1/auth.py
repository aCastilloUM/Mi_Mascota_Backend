from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.encoders import jsonable_encoder
import jwt
import logging
import time
import uuid
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_session
from app.db.repositories import UserRepo, UserSessionRepo, EmailAlreadyExists
from app.services.auth_service import AuthService, InvalidRegistration, InvalidCredentials, InvalidRefresh
from app.api.v1.schemas import (
    RegisterRequest, 
    UserOut, 
    LoginRequest, 
    TokenResponse,
    TwoFactorRequiredResponse,
    Login2FARequest,
    Login2FAResponse
)
from app.core.security import decode_token, build_refresh_cookie_value, parse_refresh_cookie_value
from app.core.config import settings
from app.events.kafka import bus
from app.services.otp_service import otp_service
from app.services.two_factor_session import two_factor_session_manager
from app.api.v1.schemas_2fa import Validate2FARequest, Validate2FAResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# --------- helpers cookie ----------
def _set_refresh_cookie(resp: Response, session_id: str, raw: str, max_age_s: int | None = None):
    resp.set_cookie(
        key=settings.refresh_cookie_name,
        value=build_refresh_cookie_value(session_id, raw),
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        domain=(settings.refresh_cookie_domain or None),
        max_age=max_age_s,
        path="/",
    )

def _clear_refresh_cookie(resp: Response):
    resp.delete_cookie(
        key=settings.refresh_cookie_name,
        domain=(settings.refresh_cookie_domain or None),
        path="/",
    )

# --------- endpoints ----------
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(payload: RegisterRequest, request: Request, session: AsyncSession = Depends(get_session)):
    svc = AuthService(UserRepo(session), UserSessionRepo(session))
    try:
        _ = payload.client.birthdate_as_date()
        # Measure time spent in register service to diagnose slow operations
        start = time.perf_counter()
        user = await svc.register(payload)
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("register_service_duration_ms", extra={"duration_ms": duration_ms, "request_id": getattr(request.state, "request_id", "-")})
        # If the service returned a development-only payload including verification_token,
        # return a JSONResponse that includes the token (bypass response_model filtering).
        if isinstance(user, dict) and user.get("verification_token"):
            # user['user'] may already be a UserOut-like object or dict
            raw_user = user.get("user")
            out = UserOut.model_validate(raw_user)
            from fastapi.responses import JSONResponse
            payload_out = out.model_dump()
            payload_out["verification_token"] = user.get("verification_token")
            # Ensure datetimes are converted to JSON-serializable types
            return JSONResponse(content=jsonable_encoder(payload_out), status_code=status.HTTP_201_CREATED)

        out = UserOut.model_validate(user)

        # ---- Kafka: user_registered ----
        try:
            # Schedule Kafka publish as a background task so registration
            # response is not delayed by Kafka connectivity or retries.
            event_id = str(uuid.uuid4())
            now_ms = int(time.time() * 1000)
            headers = [
                ("event-type", b"user_registered"),
                ("event-id", event_id.encode("utf-8")),
                ("content-type", b"application/json"),
                ("request-id", getattr(request.state, "request_id", "-").encode("utf-8")),
            ]

            async def _publish_safe(topic, key, value, headers):
                try:
                    await bus.publish(topic, key=key, value=value, headers=headers)
                    logger.info(
                        "event_published",
                        extra={
                            "event": "user_registered",
                            "user_id": out.id,
                            "event_id": event_id,
                            "request_id": getattr(request.state, "request_id", "-"),
                        }
                    )
                except Exception as e:
                    # No fallar el registro si Kafka falla; loguear error para auditoría
                    logger.error(
                        "kafka_publish_failed",
                        extra={"event": "user_registered", "user_id": out.id, "error": str(e)}
                    )

            # Create background task and do not await it
            try:
                asyncio.create_task(
                    _publish_safe(
                        settings.user_registered_topic,
                        out.id,
                        {
                            "event": "user_registered",
                            "id": event_id,
                            "ts": now_ms,
                            "v": 1,
                            "payload": {
                                "user_id": out.id,
                                "email": out.email,
                                "full_name": out.full_name,
                            },
                            "source": "auth-svc",
                        },
                        headers,
                    )
                )
            except Exception as e:
                # Scheduling the background task failed; log but don't fail the request
                logger.error("kafka_publish_schedule_failed", extra={"error": str(e), "user_id": out.id})
        except Exception:
            # Any unexpected error here should not break the registration flow
            logger.exception("unexpected_error_while_scheduling_kafka_publish")
        # -------------------------------

        return out

    except EmailAlreadyExists:
        raise HTTPException(status_code=409, detail={"code": "EMAIL_TAKEN", "message": "Ese email ya tiene cuenta"})
    except InvalidRegistration as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_REGISTRATION", "message": e.message})
    except Exception:
        logger.exception("Fallo en /api/v1/auth/register")
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR"})

@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    """
    Login con soporte para 2FA.
    
    **Flujo sin 2FA:**
    - Retorna access_token directamente
    
    **Flujo con 2FA:**
    - Retorna requires_2fa=True y temp_session_id
    - Cliente debe llamar a POST /api/v1/auth/login/2fa con el código
    """
    svc = AuthService(UserRepo(session), UserSessionRepo(session))
    try:
        ua = request.headers.get("user-agent")
        ip = request.client.host if request.client else None

        result = await svc.login_issue_tokens(
            payload.email, payload.password, user_agent=ua, ip=ip
        )
        
        # Verificar si requiere 2FA
        if isinstance(result, tuple) and len(result) == 2 and result[0] == "2FA_REQUIRED":
            temp_session_id = result[1]
            return TwoFactorRequiredResponse(temp_session_id=temp_session_id)
        
        # Login normal (sin 2FA)
        access, session_id, raw, exp = result

        # set cookie con refresh
        max_age = settings.refresh_token_ttl_seconds
        _set_refresh_cookie(response, session_id, raw, max_age_s=max_age)

        return TokenResponse(access_token=access)
    except HTTPException:
        # Re-raise HTTPException (429 de rate limiting viene desde AuthService)
        raise
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Email o contraseña inválidos"})
    except Exception:
        logger.exception("Fallo en /api/v1/auth/login")
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR"})

@router.post("/login/2fa", response_model=Login2FAResponse)
async def login_2fa(
    payload: Login2FARequest, 
    request: Request, 
    response: Response, 
    session: AsyncSession = Depends(get_session)
):
    """
    Segundo paso del login cuando 2FA está habilitado.
    
    **Requiere:**
    - temp_session_id: Obtenido del POST /api/v1/auth/login
    - token: Código 2FA de 6 dígitos o código de respaldo (XXXX-XXXX)
    
    **Rate Limiting:** Máximo 5 intentos por sesión temporal (5 minutos)
    """
    svc = AuthService(UserRepo(session), UserSessionRepo(session))
    try:
        access, session_id, raw, exp, backup_used, backup_remaining = await svc.validate_2fa_and_issue_tokens(
            temp_session_id=payload.temp_session_id,
            token=payload.token
        )
        
        # Set cookie con refresh
        max_age = settings.refresh_token_ttl_seconds
        _set_refresh_cookie(response, session_id, raw, max_age_s=max_age)
        
        result = Login2FAResponse(access_token=access)
        if backup_used:
            result.backup_code_used = True
            result.backup_codes_remaining = backup_remaining
        
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("Fallo en /api/v1/auth/login/2fa")
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR"})


@router.post("/2fa/send-otp")
async def send_otp(
    payload: Validate2FARequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Enviar o re-enviar OTP por email para una sesión temporal de 2FA."""
    try:
        pending = await two_factor_session_manager.get_pending_session(payload.session_id)
        if not pending:
            raise HTTPException(status_code=400, detail={"code": "INVALID_SESSION", "message": "Sesión temporal inválida o expirada"})

        user_repo = UserRepo(session)
        user = await user_repo.get_by_id(pending.get("user_id"))
        if not user:
            raise HTTPException(status_code=400, detail={"code": "INVALID_SESSION", "message": "Usuario no encontrado"})

        can = await otp_service.can_resend(payload.session_id)
        if not can:
            raise HTTPException(status_code=429, detail={"code": "OTP_RESEND_COOLDOWN", "message": "Reenvío bloqueado temporalmente. Intentá más tarde."})

        sent = await otp_service.create_and_send(payload.session_id, to_email=user.email)
        if not sent:
            raise HTTPException(status_code=500, detail={"code": "EMAIL_SEND_FAILED", "message": "No se pudo enviar el email. Contactá soporte."})

        return {"ok": True, "message": "OTP enviado (si el email está disponible)."}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Fallo en /api/v1/auth/2fa/send-otp")
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR"})


@router.post("/2fa/verify-otp", response_model=TokenResponse)
async def verify_otp(
    payload: Validate2FARequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Verificar OTP enviado por email y emitir tokens finales."""
    svc = AuthService(UserRepo(session), UserSessionRepo(session))
    try:
        # Validate OTP against Redis
        valid = await otp_service.validate(payload.session_id, payload.token)
        if not valid:
            raise HTTPException(status_code=400, detail={"code": "INVALID_OTP", "message": "Código OTP inválido o expirado"})

        # Issue tokens
        access, session_id, raw, exp = await svc.issue_tokens_for_pending_session(payload.session_id)

        # set cookie with refresh
        max_age = settings.refresh_token_ttl_seconds
        _set_refresh_cookie(response, session_id, raw, max_age_s=max_age)

        return TokenResponse(access_token=access)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Fallo en /api/v1/auth/2fa/verify-otp")
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR"})

@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, session: AsyncSession = Depends(get_session)):
    svc = AuthService(UserRepo(session), UserSessionRepo(session))
    try:
        cookie = request.cookies.get(settings.refresh_cookie_name)
        parsed = parse_refresh_cookie_value(cookie or "")
        if not parsed:
            raise InvalidRefresh("Cookie inválida")
        session_id, raw = parsed

        access, new_raw, new_exp = await svc.refresh_rotate(session_id, raw, user_agent=request.headers.get("user-agent"), ip=(request.client.host if request.client else None))

        # rotamos cookie
        _set_refresh_cookie(response, session_id, new_raw, max_age_s=settings.refresh_token_ttl_seconds)
        return TokenResponse(access_token=access)

    except InvalidRefresh as e:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail={"code": "INVALID_REFRESH", "message": e.message})
    except Exception:
        logger.exception("Fallo en /api/v1/auth/refresh")
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR"})

@router.post("/logout")
async def logout(request: Request, response: Response, db_session: AsyncSession = Depends(get_session)):
    svc = AuthService(UserRepo(db_session), UserSessionRepo(db_session))
    try:
        cookie = request.cookies.get(settings.refresh_cookie_name)
        parsed = parse_refresh_cookie_value(cookie or "")
        if parsed:
            session_id, _ = parsed
            logger.info(f"Revocando sesión: {session_id}")
            await svc.logout(session_id)
            logger.info(f"Sesión revocada: {session_id}")
        _clear_refresh_cookie(response)
        return {"ok": True}
    except Exception as e:
        logger.exception("Fallo en /api/v1/auth/logout")
        _clear_refresh_cookie(response)
        raise  # propagar el error para debugging

# (ya lo tenías)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
@router.get("/me", response_model=UserOut)
async def me(creds: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
             session: AsyncSession = Depends(get_session)):
    try:
        claims = decode_token(creds.credentials)
        user_id = claims.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN"})
        repo = UserRepo(session)    
        user = await repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN"})
        return UserOut.model_validate(user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"code": "TOKEN_EXPIRED"})
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail={"code": "INVALID_TOKEN"})
