# services/auth-svc/app/api/v1/schemas_email.py
"""
Schemas para email verification y password reset
"""
from pydantic import BaseModel, EmailStr, Field


# ==================== EMAIL VERIFICATION ====================
class VerifyEmailRequest(BaseModel):
    """Request para verificar email con token"""
    token: str = Field(..., min_length=1, description="Token de verificación recibido por email")


class ResendVerificationRequest(BaseModel):
    """Request para reenviar email de verificación"""
    email: EmailStr = Field(..., description="Email del usuario")


class EmailVerificationResponse(BaseModel):
    """Response de verificación de email"""
    message: str = Field(..., description="Mensaje de confirmación")
    email_verified: bool = Field(..., description="Estado de verificación")


# ==================== PASSWORD RESET ====================
class ForgotPasswordRequest(BaseModel):
    """Request para solicitar reset de contraseña"""
    email: EmailStr = Field(..., description="Email del usuario")


class ResetPasswordRequest(BaseModel):
    """Request para resetear contraseña con token"""
    token: str = Field(..., min_length=1, description="Token de reset recibido por email")
    new_password: str = Field(..., min_length=8, max_length=100, description="Nueva contraseña")


class PasswordResetResponse(BaseModel):
    """Response de operaciones de password reset"""
    message: str = Field(..., description="Mensaje de confirmación")


# ==================== CHANGE PASSWORD ====================
class ChangePasswordRequest(BaseModel):
    """Request para cambiar contraseña (usuario autenticado)"""
    old_password: str = Field(..., min_length=1, description="Contraseña actual")
    new_password: str = Field(..., min_length=8, max_length=100, description="Nueva contraseña")


class ChangePasswordResponse(BaseModel):
    """Response de cambio de contraseña"""
    message: str = Field(..., description="Mensaje de confirmación")
