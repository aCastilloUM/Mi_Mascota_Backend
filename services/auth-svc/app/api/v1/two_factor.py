# services/auth-svc/app/api/v1/two_factor.py
"""
Endpoints para 2FA TOTP
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime, timezone
import logging

from app.core.deps import get_session
from app.db.repositories import UserRepo, TwoFactorRepo
from app.services.totp_service import totp_service, TOTPService
from app.core.security import verify_password
from app.api.v1.schemas_2fa import (
    Enable2FAResponse,
    Verify2FASetupRequest,
    Verify2FASetupResponse,
    Disable2FARequest,
    Disable2FAResponse,
    RegenerateBackupCodesRequest,
    RegenerateBackupCodesResponse,
    TwoFactorStatusResponse,
)

router = APIRouter(prefix="/auth/2fa", tags=["Two-Factor Authentication"])
logger = logging.getLogger(__name__)


@router.post("/enable", response_model=Enable2FAResponse)
async def enable_2fa(
    session: AsyncSession = Depends(get_session),
    x_user_id: str = Header(..., description="User ID desde el Gateway"),
):
    """
    Inicia el proceso de habilitar 2FA.
    
    **Paso 1 de 2:** Genera QR code y códigos de respaldo.
    
    **Flujo:**
    1. Usuario solicita habilitar 2FA
    2. Backend genera: secret, QR code, backup codes
    3. Usuario escanea QR code con app (Google Authenticator, Authy)
    4. Usuario guarda códigos de respaldo
    5. Usuario verifica con código (ver /verify-setup)
    
    **IMPORTANTE:** El secret se retorna solo una vez. Guardarlo temporalmente
    hasta completar verificación.
    """
    try:
        user_id = UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="User ID inválido")
    
    users = UserRepo(session)
    user = await users.get_by_id(str(user_id))
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if user.two_factor_enabled:
        raise HTTPException(
            status_code=400,
            detail="2FA ya está habilitado. Deshabilítalo primero si querés regenerar."
        )
    
    # Generar secret, QR y backup codes
    secret, qr_code, backup_codes = totp_service.setup_2fa(user.email)
    
    logger.info(
        "2fa_enable_initiated",
        extra={"user_id": str(user_id), "email": user.email}
    )
    
    return Enable2FAResponse(
        secret=secret,
        qr_code=qr_code,
        backup_codes=backup_codes,
        message="Escaneá el QR code con tu app de autenticación (Google Authenticator, Authy, etc.) y guardá los códigos de respaldo en un lugar seguro."
    )


@router.post("/verify-setup", response_model=Verify2FASetupResponse)
async def verify_2fa_setup(
    payload: Verify2FASetupRequest,
    session: AsyncSession = Depends(get_session),
    x_user_id: str = Header(..., description="User ID desde el Gateway"),
):
    """
    Completa el proceso de habilitar 2FA.
    
    **Paso 2 de 2:** Verifica que el usuario configuró correctamente la app.
    
    **Flujo:**
    1. Usuario ingresa código de 6 dígitos de la app
    2. Backend verifica código con el secret
    3. Si es válido, habilita 2FA y guarda secret + backup codes
    
    **IMPORTANTE:** Después de esto, el secret ya no se mostrará. Guardá los
    códigos de respaldo que se retornan (última oportunidad).
    """
    try:
        user_id = UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="User ID inválido")
    
    users = UserRepo(session)
    user = await users.get_by_id(str(user_id))
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA ya está habilitado")
    
    # Verificar código TOTP
    if not totp_service.verify_totp(payload.secret, payload.token):
        raise HTTPException(
            status_code=400,
            detail="Código inválido. Verificá que esté bien configurado."
        )
    
    # Hashear backup codes antes de guardar
    backup_codes = totp_service.generate_backup_codes()
    backup_codes_hashed = [
        totp_service.hash_backup_code(code)
        for code in backup_codes
    ]
    
    # Guardar en DB
    two_factor_repo = TwoFactorRepo(session)
    await two_factor_repo.enable_2fa(
        user_id=str(user_id),
        secret=payload.secret,
        backup_codes_hashed=backup_codes_hashed
    )
    
    logger.info(
        "2fa_enabled",
        extra={"user_id": str(user_id), "email": user.email}
    )
    
    return Verify2FASetupResponse(
        message="¡2FA habilitado exitosamente! Guardá estos códigos de respaldo en un lugar seguro.",
        two_factor_enabled=True,
        backup_codes=backup_codes
    )


@router.post("/disable", response_model=Disable2FAResponse)
async def disable_2fa(
    payload: Disable2FARequest,
    session: AsyncSession = Depends(get_session),
    x_user_id: str = Header(..., description="User ID desde el Gateway"),
):
    """
    Deshabilita 2FA para el usuario.
    
    **Requiere:**
    - Contraseña actual (seguridad)
    - Código TOTP actual (confirmar que tiene acceso a la app)
    
    **ADVERTENCIA:** Esto deshabilitará la capa extra de seguridad.
    """
    try:
        user_id = UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="User ID inválido")
    
    users = UserRepo(session)
    user = await users.get_by_id(str(user_id))
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if not user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA no está habilitado")
    
    # Verificar contraseña
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña incorrecta")
    
    # Verificar código TOTP
    if not totp_service.verify_totp(user.two_factor_secret, payload.token):
        raise HTTPException(status_code=400, detail="Código 2FA inválido")
    
    # Deshabilitar
    two_factor_repo = TwoFactorRepo(session)
    await two_factor_repo.disable_2fa(str(user_id))
    
    logger.warning(
        "2fa_disabled",
        extra={"user_id": str(user_id), "email": user.email}
    )
    
    return Disable2FAResponse(
        message="2FA deshabilitado. Tu cuenta ahora tiene solo 1 factor de seguridad.",
        two_factor_enabled=False
    )


@router.post("/regenerate-backup-codes", response_model=RegenerateBackupCodesResponse)
async def regenerate_backup_codes(
    payload: RegenerateBackupCodesRequest,
    session: AsyncSession = Depends(get_session),
    x_user_id: str = Header(..., description="User ID desde el Gateway"),
):
    """
    Regenera códigos de respaldo.
    
    **Casos de uso:**
    - Usaste algunos códigos y querés regenerar todos
    - Perdiste los códigos originales (pero todavía tenés acceso a la app)
    
    **IMPORTANTE:** Esto invalida los códigos anteriores.
    """
    try:
        user_id = UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="User ID inválido")
    
    users = UserRepo(session)
    user = await users.get_by_id(str(user_id))
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if not user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2FA no está habilitado")
    
    # Verificar contraseña
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña incorrecta")
    
    # Verificar código TOTP
    if not totp_service.verify_totp(user.two_factor_secret, payload.token):
        raise HTTPException(status_code=400, detail="Código 2FA inválido")
    
    # Generar nuevos códigos
    backup_codes = totp_service.generate_backup_codes()
    backup_codes_hashed = [
        totp_service.hash_backup_code(code)
        for code in backup_codes
    ]
    
    # Actualizar en DB
    two_factor_repo = TwoFactorRepo(session)
    await two_factor_repo.update_backup_codes(str(user_id), backup_codes_hashed)
    
    logger.info(
        "2fa_backup_codes_regenerated",
        extra={"user_id": str(user_id), "email": user.email}
    )
    
    return RegenerateBackupCodesResponse(
        backup_codes=backup_codes,
        message="Nuevos códigos de respaldo generados. Los anteriores ya no funcionan."
    )


@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    session: AsyncSession = Depends(get_session),
    x_user_id: str = Header(..., description="User ID desde el Gateway"),
):
    """
    Obtiene el estado de 2FA del usuario.
    
    **Info retornada:**
    - ¿2FA habilitado?
    - Fecha de activación
    - Códigos de respaldo restantes
    """
    try:
        user_id = UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="User ID inválido")
    
    users = UserRepo(session)
    user = await users.get_by_id(str(user_id))
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    backup_codes_remaining = 0
    if user.two_factor_backup_codes:
        backup_codes_remaining = len(user.two_factor_backup_codes)
    
    enabled_at = None
    if user.two_factor_enabled_at:
        enabled_at = user.two_factor_enabled_at.isoformat()
    
    return TwoFactorStatusResponse(
        two_factor_enabled=user.two_factor_enabled,
        two_factor_enabled_at=enabled_at,
        backup_codes_remaining=backup_codes_remaining
    )
