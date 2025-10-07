# services/auth-svc/app/api/v1/schemas.py
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from datetime import date, datetime
from typing import Optional

MIN_PWD_LEN = 10

class Ubication(BaseModel):
    department: str
    city: str
    postalCode: str
    street: str
    number: str
    apartment: Optional[str] = None

class BaseUserIn(BaseModel):
    name: str
    secondName: str
    email: EmailStr
    documentType: str
    document: str
    ubication: Ubication
    password: str = Field(min_length=MIN_PWD_LEN)

    @field_validator("password")
    @classmethod
    def strong_password(cls, v: str) -> str:
        import re
        if len(v) < MIN_PWD_LEN: raise ValueError("Mínimo 10 caracteres")
        if not re.search(r"[A-Z]", v): raise ValueError("Agregá al menos 1 mayúscula")
        if not re.search(r"[a-z]", v): raise ValueError("Agregá al menos 1 minúscula")
        if not re.search(r"[0-9]", v): raise ValueError("Agregá al menos 1 número")
        if not re.search(r"[^A-Za-z0-9]", v): raise ValueError("Agregá al menos 1 símbolo")
        if re.search(r"\s", v): raise ValueError("No uses espacios")
        return v

class ClientIn(BaseModel):
    birthDate: str  # viene como "dd/MM/yyyy" desde el front

    def birthdate_as_date(self) -> date:
        txt = self.birthDate.strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(txt, fmt).date()
            except ValueError:
                continue
        raise ValueError("Fecha inválida, formato esperado dd/MM/yyyy")

class RegisterRequest(BaseModel):
    baseUser: BaseUserIn
    client: ClientIn


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    status: str
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TwoFactorRequiredResponse(BaseModel):
    """
    Respuesta cuando el login requiere 2FA.
    El cliente debe llamar a POST /api/v1/auth/login/2fa con el temp_session_id y el código.
    """
    requires_2fa: bool = True
    temp_session_id: str
    message: str = "Se requiere código 2FA para completar el login"

class Login2FARequest(BaseModel):
    """
    Segundo paso del login cuando 2FA está habilitado.
    """
    temp_session_id: str
    token: str = Field(..., min_length=6, max_length=6, description="Código 2FA de 6 dígitos o código de respaldo (XXXX-XXXX)")
    
    @field_validator("token")
    @classmethod
    def validate_token_format(cls, v: str) -> str:
        v = v.strip()
        # Permitir 6 dígitos (TOTP) o formato XXXX-XXXX (backup code)
        import re
        if re.match(r"^\d{6}$", v):  # TOTP
            return v
        if re.match(r"^\w{4}-\w{4}$", v):  # Backup code
            return v
        raise ValueError("Token debe ser 6 dígitos (TOTP) o formato XXXX-XXXX (código de respaldo)")
    
class Login2FAResponse(BaseModel):
    """
    Respuesta exitosa después de validar 2FA.
    """
    access_token: str
    token_type: str = "bearer"
    backup_code_used: Optional[bool] = None
    backup_codes_remaining: Optional[int] = None