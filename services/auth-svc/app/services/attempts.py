# app/services/attempts.py
import time
from typing import Optional
from app.infra.redis import redis_client
from app.core.config import settings

# Claves:
#  - intentos por ventana: login:attempts:{email}:{ip}
#  - bloqueo:              login:block:{email}:{ip}

class LoginAttemptTracker:
    def __init__(self) -> None:
        self.window = settings.login_window_seconds
        self.max_attempts = settings.login_max_attempts
        self.block_seconds = settings.login_block_seconds

    def _key_attempts(self, email: str, ip: str) -> str:
        return f"login:attempts:{email}:{ip}"

    def _key_block(self, email: str, ip: str) -> str:
        return f"login:block:{email}:{ip}"

    async def check_blocked(self, email: str, ip: str) -> int:
        """Devuelve segundos restantes de bloqueo o 0 si no está bloqueado."""
        ttl = await redis_client.conn.ttl(self._key_block(email, ip))
        return max(ttl, 0)

    async def register_failure(self, email: str, ip: str) -> Optional[int]:
        """
        Incrementa contador de intentos. Si supera el límite, activa bloqueo y devuelve
        segundos de bloqueo. Si no, devuelve None.
        """
        k = self._key_attempts(email, ip)
        # INCR y setear TTL solo si es primera vez
        count = await redis_client.conn.incr(k)
        if count == 1:
            await redis_client.conn.expire(k, self.window)

        if count >= self.max_attempts:
            # setea bloqueo
            bkey = self._key_block(email, ip)
            # solo setea si no existe (NX) para no sobreescribir TTL
            await redis_client.conn.set(bkey, "1", ex=self.block_seconds, nx=True)
            return self.block_seconds
        return None

    async def reset(self, email: str, ip: str) -> None:
        """Resetea el contador de intentos (no toca el bloqueo)"""
        await redis_client.conn.delete(self._key_attempts(email, ip))
