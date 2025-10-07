# services/auth-svc/app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import logging
import time
import uuid

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
        user = await svc.register(payload)
        out = UserOut.model_validate(user)

        # ---- Kafka: user_registered ----
        try:
            event_id = str(uuid.uuid4())
            now_ms = int(time.time() * 1000)
            headers = [
                ("event-type", b"user_registered"),
                ("event-id", event_id.encode("utf-8")),
                ("content-type", b"application/json"),
                ("request-id", getattr(request.state, "request_id", "-").encode("utf-8")),
            ]
            await bus.publish(
                settings.user_registered_topic,
                key=out.id,  # particiona por usuario
                value={
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
                headers=headers,
            )
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
            # No fallar el registro si Kafka falla
            logger.error(
                "kafka_publish_failed",
                extra={"event": "user_registered", "user_id": out.id, "error": str(e)}
            )
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
