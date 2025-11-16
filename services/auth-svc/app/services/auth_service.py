# services/auth-svc/app/services/auth.py
from datetime import date, datetime, timedelta, timezone
import time
from fastapi import HTTPException
from app.api.v1.schemas import RegisterRequest, UserOut
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token_raw,
    hash_refresh_token,
    verify_refresh_token,
)
from app.db.repositories import UserRepo, EmailAlreadyExists, UserSessionRepo
from app.services.attempts import LoginAttemptTracker
from app.services.email_service import email_service
from app.services.totp_service import totp_service
from app.services.two_factor_session import two_factor_session_manager
from app.services.otp_service import otp_service
from app.core.config import settings
import secrets
from uuid import UUID
import logging
from app.events.kafka import bus
import asyncio
import httpx

logger = logging.getLogger(__name__)

class InvalidRegistration(Exception):
    def __init__(self, message: str): self.message = message

class InvalidCredentials(Exception):
    def __init__(self, message: str): self.message = message

class InvalidRefresh(Exception):
    def __init__(self, message: str): self.message = message

class EmailVerificationError(Exception):
    def __init__(self, message: str): self.message = message

class PasswordResetError(Exception):
    def __init__(self, message: str): self.message = message

class AuthService:
    def __init__(self, users: UserRepo, sessions: UserSessionRepo | None = None):
        self.users = users
        self.sessions = sessions
        self.attempts = LoginAttemptTracker()

    async def register(self, payload: RegisterRequest) -> UserOut:
        # edad >= 16
        birth: date = payload.client.birthdate_as_date()
        today = date.today()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        if age < 16:
            raise InvalidRegistration("Debés ser mayor de 16 años")

        full_name = f"{payload.baseUser.name.strip()} {payload.baseUser.secondName.strip()}".strip()
        email = payload.baseUser.email.strip().lower()
        pwd_hash = hash_password(payload.baseUser.password)

        try:
            start_create = time.perf_counter()
            user = await self.users.create(email=email, password_hash=pwd_hash, full_name=full_name)
            create_ms = int((time.perf_counter() - start_create) * 1000)
            logger.info("user_create_duration_ms", extra={"ms": create_ms, "email": email})
        except EmailAlreadyExists:
            raise InvalidRegistration("Ese email ya tiene cuenta")

        # Generar token de verificación y enviar email
        verification_token = secrets.token_urlsafe(32)
        try:
            start_token = time.perf_counter()
            await self.users.update_email_verification_token(user.id, verification_token)
            token_ms = int((time.perf_counter() - start_token) * 1000)
            logger.info("update_email_verification_token_duration_ms", extra={"ms": token_ms, "user_id": str(user.id)})
        except Exception:
            logger.exception("failed_update_email_verification_token")

        # Enviar email de verificación en background (no await) para no bloquear
        try:
            asyncio.create_task(
                email_service.send_verification_email(
                    to_email=user.email,
                    user_name=user.full_name,
                    token=verification_token
                )
            )
        except Exception:
            logger.exception("failed_to_schedule_verification_email")

        # Try to synchronously create a profile in profile-svc so the profile
        # exists immediately after registration (even if login is blocked until
        # email verification). This is a best-effort, non-blocking on failure.
        if settings.profile_svc_url:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    url = settings.profile_svc_url.rstrip("/") + "/internal/profiles"
                    payload = {"user_id": str(user.id), "email": user.email, "display_name": user.full_name}
                    resp = await client.post(url, json=payload)
                    if resp.status_code >= 400:
                        logger.warning("profile_sync_on_register_failed", extra={"status_code": resp.status_code, "text": resp.text})
            except Exception:
                logger.exception("profile_sync_request_failed_on_register")

        # Optionally expose the verification token in development for local testing.
        # Controlled by the EXPOSE_DEV_VERIFICATION_TOKEN env var (default: false).
        if getattr(settings, "expose_dev_verification_token", False):
            logger.info("verification_token_generated", extra={"user_id": str(user.id), "token": verification_token})
            u = UserOut(
                id=str(user.id),
                email=user.email,
                full_name=user.full_name,
                status=user.status.value if hasattr(user.status, "value") else str(user.status),
                created_at=getattr(user, "created_at", None),
            )
            # Attach token for dev convenience
            return {"user": u, "verification_token": verification_token}

        return UserOut(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            status=user.status.value if hasattr(user.status, "value") else str(user.status),
            created_at=getattr(user, "created_at", None),
        )

    async def login_issue_tokens(self, email: str, password: str, *, user_agent: str | None, ip: str | None):
        if self.sessions is None:
            raise RuntimeError("UserSessionRepo no inyectado")

        norm = email.strip().lower()
        client_ip = ip or "-"

        # 1) ¿bloqueado?
        secs = await self.attempts.check_blocked(norm, client_ip)
        if secs > 0:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "TOO_MANY_ATTEMPTS", 
                    "retry_after": secs, 
                    "message": "Demasiados intentos. Probá más tarde."
                }
            )

        # 2) Verificar credenciales
        user = await self.users.get_by_email(norm)
        if not user or not verify_password(password, user.password_hash):
            # Si el usuario existe, incrementar contador de intentos fallidos
            if user:
                failed_count = await self.users.increment_failed_attempts(user.id)
                
                # Si alcanza el threshold, bloquear cuenta
                if failed_count >= settings.account_lock_threshold:
                    lock_until = datetime.now(timezone.utc) + timedelta(
                        minutes=settings.account_lock_duration_minutes
                    )
                    await self.users.lock_account(user.id, lock_until)
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "code": "ACCOUNT_LOCKED",
                            "message": f"Cuenta bloqueada por {settings.account_lock_duration_minutes} minutos debido a múltiples intentos fallidos",
                            "retry_after": settings.account_lock_duration_minutes * 60
                        }
                    )
            
            # Registrar fallo en rate limiter (legacy)
            maybe_block = await self.attempts.register_failure(norm, client_ip)
            if maybe_block:
                # Primer 429 de bloqueo
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "TOO_MANY_ATTEMPTS", 
                        "retry_after": maybe_block, 
                        "message": "Demasiados intentos. Probá más tarde."
                    }
                )
            # Si todavía no bloquea, 401
            raise InvalidCredentials("Email o contraseña inválidos")

        # 2.5) Verificar si la cuenta está bloqueada
        if user.locked_until:
            now = datetime.now(timezone.utc)
            if user.locked_until > now:
                remaining_seconds = int((user.locked_until - now).total_seconds())
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "ACCOUNT_LOCKED",
                        "message": "Cuenta temporalmente bloqueada",
                        "retry_after": remaining_seconds
                    }
                )
            else:
                # Desbloquear automáticamente si ya pasó el tiempo
                await self.users.reset_failed_attempts(user.id)

        # 3) Login exitoso: resetear contador
        await self.attempts.reset(norm, client_ip)
        await self.users.reset_failed_attempts(user.id)

        # 3.1) Verificar si el email está verificado
        # Si el flujo requiere verificación de email (por política), impedir login hasta que se verifique.
        if not user.email_verified:
            # No permitir login hasta verificar el email
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "EMAIL_NOT_VERIFIED",
                    "message": "El email no está verificado. Revisa tu correo o solicita reenvío de verificación."
                }
            )

        # 3.5) VERIFICAR SI TIENE 2FA HABILITADO
        if user.two_factor_enabled:
            # NO generar tokens todavía, crear sesión temporal
            temp_session_id = await two_factor_session_manager.create_pending_session(
                user_id=str(user.id),
                user_agent=user_agent,
                ip=ip,
            )
            # Generate and send OTP via email for initial email-based 2FA flow
            try:
                await otp_service.create_and_send(temp_session_id, to_email=user.email)
            except Exception:
                logger.exception("failed_to_send_otp_email")

            logger.info(
                "2fa_required_for_login",
                extra={"user_id": str(user.id), "email": user.email},
            )
            # Retornar un valor especial que el endpoint interpretará
            # Usamos una tupla de 2 elementos: (requires_2fa, temp_session_id)
            return ("2FA_REQUIRED", temp_session_id)

        # 4) Generar tokens (solo si NO tiene 2FA)
        access = create_access_token(sub=str(user.id))

        # refresh
        raw = generate_refresh_token_raw()
        rhash = hash_refresh_token(raw)
        expires = datetime.now(timezone.utc) + timedelta(seconds=1209600)  # 14 días por defecto; o usa settings

        session = await self.sessions.create(
            user_id=str(user.id),
            refresh_token_hash=rhash,
            user_agent=user_agent,
            ip=ip,
            expires_at=expires,
        )
        return access, str(session.id), raw, expires

    async def issue_tokens_for_pending_session(self, temp_session_id: str) -> tuple[str, str, str, datetime]:
        """
        After a pending session has been validated (e.g. OTP validated),
        issue access + refresh tokens for the user referenced by the pending session.
        Returns: access, session_id, raw_refresh, expires
        """
        if self.sessions is None:
            raise RuntimeError("UserSessionRepo no inyectado")

        pending = await two_factor_session_manager.get_pending_session(temp_session_id)
        if not pending:
            raise HTTPException(status_code=400, detail="Sesión 2FA inválida o expirada")

        user_id = pending.get("user_id")
        user_agent = pending.get("user_agent")
        ip = pending.get("ip")

        user = await self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=400, detail="Usuario no encontrado")

        # delete pending session
        await two_factor_session_manager.delete_pending_session(temp_session_id)

        # generate tokens
        access = create_access_token(sub=str(user.id))
        raw = generate_refresh_token_raw()
        rhash = hash_refresh_token(raw)
        expires = datetime.now(timezone.utc) + timedelta(seconds=1209600)

        session = await self.sessions.create(
            user_id=str(user.id),
            refresh_token_hash=rhash,
            user_agent=user_agent,
            ip=ip,
            expires_at=expires,
        )

        return access, str(session.id), raw, expires

    async def refresh_rotate(self, session_id: str, raw_token: str, *, user_agent: str | None, ip: str | None):
        if self.sessions is None:
            raise RuntimeError("UserSessionRepo no inyectado")

        session = await self.sessions.get_by_id(session_id)
        if not session:
            raise InvalidRefresh("Sesión inválida")

        # checks básicos - verificar revocación PRIMERO
        if session.revoked_at is not None:
            raise InvalidRefresh("Sesión revocada")
        
        now = datetime.now(timezone.utc)
        if session.expires_at is None or session.expires_at <= now:
            raise InvalidRefresh("Sesión expirada")

        if not verify_refresh_token(raw_token, session.refresh_token_hash):
            raise InvalidRefresh("Refresh token inválido")

        # rotate: nuevo hash + nueva expiración
        new_raw = generate_refresh_token_raw()
        new_hash = hash_refresh_token(new_raw)
        new_exp = now + timedelta(seconds=1209600)
        # Persist rotation in DB and issue a new access token
        await self.sessions.rotate_token(session_id, new_hash, new_exp)

        # nuevo access
        access = create_access_token(sub=str(session.user_id))
        return access, new_raw, new_exp

    async def logout(self, session_id: str):
        if self.sessions is None:
            raise RuntimeError("UserSessionRepo no inyectado")
        await self.sessions.revoke(session_id)
    
    async def validate_2fa_and_issue_tokens(
        self,
        temp_session_id: str,
        token: str
    ) -> tuple[str, str, str, datetime, bool, int]:
        """
        Valida código 2FA y genera tokens si es correcto.
        
        Args:
            temp_session_id: ID de sesión temporal creado en login
            token: Código 2FA (6 dígitos TOTP o XXXX-XXXX backup code)
        
        Returns:
            Tupla de (access_token, session_id, refresh_token, expires_at, backup_code_used, backup_codes_remaining)
        
        Raises:
            HTTPException: Si el código es inválido o la sesión no existe
        """
        if self.sessions is None:
            raise RuntimeError("UserSessionRepo no inyectado")
        
        # 1) Recuperar sesión temporal
        pending = await two_factor_session_manager.get_pending_session(temp_session_id)
        if not pending:
            raise HTTPException(
                status_code=400,
                detail="Sesión 2FA inválida o expirada. Iniciá sesión nuevamente."
            )
        
        user_id = pending["user_id"]
        user_agent = pending.get("user_agent")
        ip = pending.get("ip")
        
        # 2) Obtener usuario
        user = await self.users.get_by_id(user_id)
        if not user or not user.two_factor_enabled:
            await two_factor_session_manager.delete_pending_session(temp_session_id)
            raise HTTPException(status_code=400, detail="Configuración 2FA inválida")
        
        # 3) Rate limiting: máximo 5 intentos
        attempts = await two_factor_session_manager.increment_attempts(temp_session_id)
        if attempts > 5:
            await two_factor_session_manager.delete_pending_session(temp_session_id)
            raise HTTPException(
                status_code=429,
                detail="Demasiados intentos de 2FA. Iniciá sesión nuevamente."
            )
        
        # 4) Validar código (TOTP o backup code)
        backup_code_used = False
        backup_codes_remaining = 0
        
        # Intentar primero como código TOTP (6 dígitos)
        if len(token) == 6 and token.isdigit():
            if not totp_service.verify_totp(user.two_factor_secret, token):
                raise HTTPException(
                    status_code=400,
                    detail=f"Código 2FA inválido. Intentos restantes: {6 - attempts}"
                )
        # Si no es TOTP, verificar como backup code
        else:
            if not user.two_factor_backup_codes:
                raise HTTPException(status_code=400, detail="No tenés códigos de respaldo disponibles")
            
            # Verificar código de respaldo
            if not totp_service.verify_backup_code(token, user.two_factor_backup_codes):
                raise HTTPException(
                    status_code=400,
                    detail=f"Código de respaldo inválido. Intentos restantes: {6 - attempts}"
                )
            
            # Código válido: remover de la lista (uso único)
            from app.db.repositories import TwoFactorRepo
            two_factor_repo = TwoFactorRepo(self.users.session)
            remaining = totp_service.remove_used_backup_code(token, user.two_factor_backup_codes)
            await two_factor_repo.remove_backup_code(user_id, remaining)
            
            backup_code_used = True
            backup_codes_remaining = len(remaining)
            
            logger.warning(
                "2fa_backup_code_used",
                extra={
                    "user_id": user_id,
                    "email": user.email,
                    "remaining": backup_codes_remaining
                }
            )
        
        # 5) Código válido: eliminar sesión temporal y generar tokens
        await two_factor_session_manager.delete_pending_session(temp_session_id)
        
        # 6) Generar tokens
        access = create_access_token(sub=user_id)
        raw = generate_refresh_token_raw()
        rhash = hash_refresh_token(raw)
        expires = datetime.now(timezone.utc) + timedelta(seconds=1209600)
        
        session = await self.sessions.create(
            user_id=user_id,
            refresh_token_hash=rhash,
            user_agent=user_agent,
            ip=ip,
            expires_at=expires,
        )
        
        logger.info(
            "2fa_login_successful",
            extra={
                "user_id": user_id,
                "email": user.email,
                "backup_code_used": backup_code_used
            }
        )
        
        return access, str(session.id), raw, expires, backup_code_used, backup_codes_remaining

    # ==================== EMAIL VERIFICATION ====================
    async def verify_email(self, token: str) -> bool:
        """Verifica el email del usuario con el token"""
        user = await self.users.get_by_verification_token(token)
        if not user:
            raise EmailVerificationError("Token de verificación inválido o expirado")

        # Verificar si el token no ha expirado (configurable)
        if user.email_verification_sent_at:
            token_age = datetime.now(timezone.utc) - user.email_verification_sent_at
            if token_age > timedelta(minutes=settings.email_verification_token_ttl_minutes):
                raise EmailVerificationError("El token de verificación ha expirado")

        # Marcar email como verificado
        await self.users.verify_email(user.id)

        # Publish domain event to Kafka (best-effort). This is useful for other services to react
        # e.g., profile-svc can listen for this event and mark profile as email_verified.
        try:
            await bus.publish(
                settings.user_verified_topic,
                key=str(user.id),
                value={
                    "event": "user_verified",
                    "version": 1,
                    "user_id": str(user.id),
                    "email": user.email,
                    "occurred_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                },
            )
        except Exception:
            logger.exception("failed_to_publish_user_verified_event")

        # Also try an immediate sync to profile-svc internal endpoint if configured (best-effort).
        if settings.profile_svc_url:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    url = settings.profile_svc_url.rstrip("/") + "/internal/profiles/verify"
                    payload = {"user_id": str(user.id), "email": user.email}
                    resp = await client.post(url, json=payload)
                    if resp.status_code >= 400:
                        logger.warning("profile_sync_failed", extra={"status_code": resp.status_code, "text": resp.text})
            except Exception:
                logger.exception("profile_sync_request_failed")

        return True

    async def resend_verification_email(self, email: str) -> bool:
        """Reenvía el email de verificación"""
        user = await self.users.get_by_email(email.strip().lower())
        if not user:
            raise EmailVerificationError("Usuario no encontrado")
        
        if user.email_verified:
            raise EmailVerificationError("El email ya está verificado")
        
        # Generar nuevo token
        verification_token = secrets.token_urlsafe(32)
        await self.users.update_email_verification_token(user.id, verification_token)
        
        # Enviar email
        await email_service.send_verification_email(
            to_email=user.email,
            user_name=user.full_name,
            token=verification_token
        )
        return True

    # ==================== PASSWORD RESET ====================
    async def request_password_reset(self, email: str) -> bool:
        """Solicita un reset de contraseña"""
        user = await self.users.get_by_email(email.strip().lower())
        if not user:
            # Por seguridad, no revelar que el usuario no existe
            return True
        
        # Generar token de reset
        reset_token = secrets.token_urlsafe(32)
        await self.users.update_password_reset_token(user.id, reset_token)
        
        # Enviar email
        await email_service.send_password_reset_email(
            to_email=user.email,
            user_name=user.full_name,
            token=reset_token
        )
        return True

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Resetea la contraseña con el token"""
        user = await self.users.get_by_password_reset_token(token)
        if not user:
            raise PasswordResetError("Token de reset inválido o expirado")
        
        # Verificar si el token no ha expirado (1 hora)
        if user.password_reset_sent_at:
            token_age = datetime.now(timezone.utc) - user.password_reset_sent_at
            if token_age > timedelta(minutes=settings.password_reset_token_ttl_minutes):
                raise PasswordResetError("El token de reset ha expirado")
        
        # Cambiar contraseña
        new_hash = hash_password(new_password)
        await self.users.update_password(user.id, new_hash)
        
        # Limpiar token de reset
        await self.users.clear_password_reset_token(user.id)
        
        # Enviar email de confirmación
        await email_service.send_password_changed_email(
            to_email=user.email,
            user_name=user.full_name
        )
        return True

    # ==================== CHANGE PASSWORD ====================
    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> bool:
        """Cambia la contraseña de un usuario autenticado"""
        user = await self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Verificar contraseña actual
        if not verify_password(old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
        
        # Cambiar contraseña
        new_hash = hash_password(new_password)
        await self.users.update_password(user.id, new_hash)
        
        # Enviar email de confirmación
        await email_service.send_password_changed_email(
            to_email=user.email,
            user_name=user.full_name
        )
        return True
