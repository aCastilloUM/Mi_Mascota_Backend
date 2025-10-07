# services/auth-svc/app/services/rate_limit.py
import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Tuple
from app.core.config import settings

@dataclass
class AttemptState:
    count: int
    first_ts: float
    locked_until: float  # epoch seconds; 0 si no lock

class LockoutError(Exception):
    """Se lanza cuando un usuario está bloqueado por demasiados intentos fallidos"""
    pass

class RateLimiter:
    """
    In-memory rate limiter por (email, ip).
    * Ventana deslizante (first_ts..+window)
    * Lockout si excede el máximo.
    """
    def __init__(self):
        self._data: Dict[Tuple[str, str], AttemptState] = {}
        self._lock = asyncio.Lock()
        self.window = settings.failed_login_window_seconds
        self.max_attempts = settings.failed_login_max
        self.lock_minutes = settings.login_lockout_minutes

    async def can_attempt(self, email: str, ip: str) -> None:
        """
        Verifica si el usuario puede intentar login.
        Lanza LockoutError si está bloqueado.
        """
        key = (email, ip)
        now = time.time()
        async with self._lock:
            st = self._data.get(key)
            if not st:
                return
            if st.locked_until and now < st.locked_until:
                raise LockoutError("LOCKED")
            # si pasó la ventana, resetea
            if now - st.first_ts > self.window:
                self._data.pop(key, None)

    async def record_failure(self, email: str, ip: str) -> None:
        """Registra un intento fallido de login"""
        key = (email, ip)
        now = time.time()
        async with self._lock:
            st = self._data.get(key)
            if not st:
                st = AttemptState(count=1, first_ts=now, locked_until=0)
                self._data[key] = st
            else:
                # nueva ventana si expiró
                if now - st.first_ts > self.window:
                    st.count = 1
                    st.first_ts = now
                    st.locked_until = 0
                else:
                    st.count += 1
            # bloquea si excede
            if st.count >= self.max_attempts:
                st.locked_until = now + (settings.login_lockout_minutes * 60)

    async def record_success(self, email: str, ip: str) -> None:
        """Registra un login exitoso y limpia el estado"""
        key = (email, ip)
        async with self._lock:
            self._data.pop(key, None)

# instancia global (ok para 1 proceso uvicorn)
rate_limiter = RateLimiter()
