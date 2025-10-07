# services/auth-svc/app/services/two_factor_session.py
"""
Manejo de sesiones temporales para login con 2FA.
Guarda credenciales validadas en Redis hasta que se complete el 2FA.
"""
import secrets
import json
from datetime import timedelta
from app.infra.redis import redis_client

class TwoFactorSessionManager:
    """
    Maneja sesiones temporales de 2FA durante el login.
    
    Flujo:
    1. Usuario ingresa email/password (válidos)
    2. Si tiene 2FA habilitado, guardamos user_id + metadata en Redis
    3. Retornamos temp_session_id al cliente
    4. Cliente llama con temp_session_id + código 2FA
    5. Validamos código, recuperamos user_id, generamos tokens
    6. Eliminamos sesión temporal
    """
    
    PREFIX = "2fa:pending:"
    TTL_SECONDS = 300  # 5 minutos para completar 2FA
    
    async def create_pending_session(
        self,
        user_id: str,
        user_agent: str | None,
        ip: str | None
    ) -> str:
        """
        Crea una sesión temporal para 2FA.
        
        Returns:
            temp_session_id: ID temporal para validar 2FA
        """
        temp_session_id = secrets.token_urlsafe(32)
        key = f"{self.PREFIX}{temp_session_id}"
        
        data = {
            "user_id": user_id,
            "user_agent": user_agent,
            "ip": ip
        }
        
        await redis_client.conn.setex(
            key,
            timedelta(seconds=self.TTL_SECONDS),
            json.dumps(data)
        )
        
        return temp_session_id
    
    async def get_pending_session(self, temp_session_id: str) -> dict | None:
        """
        Recupera datos de sesión temporal.
        
        Returns:
            dict con user_id, user_agent, ip o None si no existe/expiró
        """
        key = f"{self.PREFIX}{temp_session_id}"
        data = await redis_client.conn.get(key)
        
        if not data:
            return None
        
        return json.loads(data)
    
    async def delete_pending_session(self, temp_session_id: str):
        """
        Elimina sesión temporal (después de validar 2FA o por timeout).
        """
        key = f"{self.PREFIX}{temp_session_id}"
        await redis_client.conn.delete(key)
    
    async def increment_attempts(self, temp_session_id: str) -> int:
        """
        Incrementa contador de intentos fallidos de 2FA.
        Después de 5 intentos, bloquea la sesión.
        
        Returns:
            Número de intentos realizados
        """
        key = f"{self.PREFIX}{temp_session_id}:attempts"
        attempts = await redis_client.conn.incr(key)
        
        # Setear TTL en el primer intento
        if attempts == 1:
            await redis_client.conn.expire(key, self.TTL_SECONDS)
        
        return attempts


two_factor_session_manager = TwoFactorSessionManager()
