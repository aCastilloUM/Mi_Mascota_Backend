# services/auth-svc/app/api/v1/schemas_2fa.py
"""
Schemas para 2FA TOTP
"""
from pydantic import BaseModel, Field
from typing import List


# ==================== ENABLE 2FA ====================
class Enable2FAResponse(BaseModel):
    """Response al iniciar setup de 2FA"""
    secret: str = Field(..., description="Secret TOTP (guardar temporalmente)")
    qr_code: str = Field(..., description="QR code en base64 para escanear")
    backup_codes: List[str] = Field(..., description="Códigos de respaldo (guardar!)")
    message: str = Field(..., description="Instrucciones")


class Verify2FASetupRequest(BaseModel):
    """Request para verificar setup de 2FA"""
    secret: str = Field(..., description="Secret temporal del setup")
    token: str = Field(..., min_length=6, max_length=6, description="Código TOTP de 6 dígitos")


class Verify2FASetupResponse(BaseModel):
    """Response al completar setup de 2FA"""
    message: str = Field(..., description="Confirmación")
    two_factor_enabled: bool = Field(..., description="Estado de 2FA")
    backup_codes: List[str] = Field(..., description="Códigos de respaldo (¡última oportunidad para guardar!)")


# ==================== DISABLE 2FA ====================
class Disable2FARequest(BaseModel):
    """Request para deshabilitar 2FA"""
    password: str = Field(..., description="Contraseña actual para confirmar")
    token: str = Field(..., min_length=6, max_length=6, description="Código TOTP actual")


class Disable2FAResponse(BaseModel):
    """Response al deshabilitar 2FA"""
    message: str = Field(..., description="Confirmación")
    two_factor_enabled: bool = Field(..., description="Estado de 2FA")


# ==================== VALIDATE 2FA (Login) ====================
class Validate2FARequest(BaseModel):
    """Request para validar código 2FA en login"""
    session_id: str = Field(..., description="ID de sesión temporal del login")
    token: str = Field(..., min_length=6, max_length=6, description="Código TOTP de 6 dígitos")
    is_backup_code: bool = Field(default=False, description="True si es un código de respaldo")


class Validate2FAResponse(BaseModel):
    """Response al validar 2FA exitosamente"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Refresh token")
    session_id: str = Field(..., description="ID de sesión")
    expires_at: str = Field(..., description="Expiración del refresh token")
    message: str = Field(..., description="Confirmación")


# ==================== BACKUP CODES ====================
class RegenerateBackupCodesRequest(BaseModel):
    """Request para regenerar códigos de respaldo"""
    password: str = Field(..., description="Contraseña actual")
    token: str = Field(..., min_length=6, max_length=6, description="Código TOTP actual")


class RegenerateBackupCodesResponse(BaseModel):
    """Response con nuevos códigos de respaldo"""
    backup_codes: List[str] = Field(..., description="Nuevos códigos de respaldo")
    message: str = Field(..., description="Confirmación")


# ==================== STATUS ====================
class TwoFactorStatusResponse(BaseModel):
    """Response con estado de 2FA del usuario"""
    two_factor_enabled: bool = Field(..., description="¿2FA habilitado?")
    two_factor_enabled_at: str | None = Field(None, description="Fecha de activación")
    backup_codes_remaining: int = Field(..., description="Códigos de respaldo restantes")
