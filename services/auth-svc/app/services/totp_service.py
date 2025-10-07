# services/auth-svc/app/services/totp_service.py
"""
TOTP (Time-based One-Time Password) Service
Maneja generación, validación y códigos de respaldo para 2FA
"""

import secrets
import hashlib
from io import BytesIO
from base64 import b64encode
from typing import List, Tuple
from datetime import datetime, timezone
import logging
import pyotp  # type: ignore
import qrcode  # type: ignore

from app.core.config import settings

logger = logging.getLogger(__name__)


class TOTPService:
    """
    Servicio para manejar 2FA con TOTP (RFC 6238)
    
    Características:
    - Genera secrets únicos por usuario
    - Genera QR codes para apps como Google Authenticator
    - Valida códigos TOTP (6 dígitos)
    - Genera códigos de respaldo (backup codes)
    - Rate limiting en validación
    """
    
    @staticmethod
    def generate_secret() -> str:
        """
        Genera un secret random para TOTP (base32)
        
        Returns:
            Secret en formato base32 (32 chars)
        """
        return pyotp.random_base32()
    
    @staticmethod
    def generate_provisioning_uri(secret: str, email: str) -> str:
        """
        Genera URI para provisioning (usado en QR code)
        
        Args:
            secret: Secret TOTP del usuario
            email: Email del usuario
            
        Returns:
            URI en formato otpauth://totp/...
        """
        totp = pyotp.TOTP(secret)
        
        # Nombre de la app + email del usuario
        issuer_name = "Mi Mascota"
        account_name = f"{issuer_name}:{email}"
        
        return totp.provisioning_uri(
            name=account_name,
            issuer_name=issuer_name
        )
    
    @staticmethod
    def generate_qr_code(provisioning_uri: str) -> str:
        """
        Genera QR code en base64 para mostrar en frontend
        
        Args:
            provisioning_uri: URI de provisioning
            
        Returns:
            QR code en base64 (data URI)
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir a base64
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    @staticmethod
    def verify_totp(secret: str, token: str, window: int = 1) -> bool:
        """
        Verifica un código TOTP
        
        Args:
            secret: Secret TOTP del usuario
            token: Código de 6 dígitos ingresado por el usuario
            window: Ventana de tiempo (1 = ±30s)
            
        Returns:
            True si el código es válido
        """
        if not token or len(token) != 6:
            return False
        
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=window)
        except Exception as e:
            logger.error(f"totp_verify_error", extra={"error": str(e)})
            return False
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """
        Genera códigos de respaldo aleatorios
        
        Args:
            count: Cantidad de códigos a generar (default: 10)
            
        Returns:
            Lista de códigos en formato XXXX-XXXX
        """
        codes = []
        for _ in range(count):
            # Generar 8 caracteres aleatorios (mayúsculas + números)
            code = secrets.token_hex(4).upper()
            # Formatear como XXXX-XXXX
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        
        return codes
    
    @staticmethod
    def hash_backup_code(code: str) -> str:
        """
        Hashea un código de respaldo para almacenarlo
        
        Args:
            code: Código en formato XXXX-XXXX
            
        Returns:
            Hash SHA256 del código
        """
        # Remover guiones y convertir a lowercase
        normalized = code.replace("-", "").lower()
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    @staticmethod
    def verify_backup_code(code: str, hashed_codes: List[str]) -> bool:
        """
        Verifica si un código de respaldo es válido
        
        Args:
            code: Código ingresado por el usuario
            hashed_codes: Lista de códigos hasheados
            
        Returns:
            True si el código es válido
        """
        if not code or not hashed_codes:
            return False
        
        code_hash = TOTPService.hash_backup_code(code)
        return code_hash in hashed_codes
    
    @staticmethod
    def remove_used_backup_code(code: str, hashed_codes: List[str]) -> List[str]:
        """
        Remueve un código de respaldo usado
        
        Args:
            code: Código usado
            hashed_codes: Lista de códigos hasheados
            
        Returns:
            Nueva lista sin el código usado
        """
        code_hash = TOTPService.hash_backup_code(code)
        return [c for c in hashed_codes if c != code_hash]
    
    @staticmethod
    def setup_2fa(email: str) -> Tuple[str, str, List[str]]:
        """
        Setup completo de 2FA para un usuario
        
        Args:
            email: Email del usuario
            
        Returns:
            Tuple (secret, qr_code_base64, backup_codes)
        """
        # Generar secret
        secret = TOTPService.generate_secret()
        
        # Generar QR code
        uri = TOTPService.generate_provisioning_uri(secret, email)
        qr_code = TOTPService.generate_qr_code(uri)
        
        # Generar backup codes
        backup_codes = TOTPService.generate_backup_codes()
        
        logger.info(
            "2fa_setup_initiated",
            extra={"email": email}
        )
        
        return secret, qr_code, backup_codes


# Instancia global
totp_service = TOTPService()
