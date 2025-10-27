"""
One-time Password (OTP) service for email-based 2FA.

Features:
- Generate numeric OTPs (configurable length)
- Hash OTPs before storing (SHA256) and store metadata in Redis with TTL
- Enforce resend cooldown and attempt limits per user/temp_session
- Validate OTPs and invalidate on success
- Expose high-level helpers used by AuthService and API
"""
import secrets
import hashlib
import time
import logging
from typing import Optional
from datetime import timedelta

from app.core.config import settings
from app.infra.redis import redis_client
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


class OTPService:
    PREFIX = "otp:code:"
    RESEND_PREFIX = "otp:resend:"
    ATTEMPT_PREFIX = "otp:attempts:"

    def __init__(self):
        self.length = settings.otp_length if hasattr(settings, "otp_length") else 6
        self.ttl = settings.otp_ttl_seconds if hasattr(settings, "otp_ttl_seconds") else 300
        self.resend_cooldown = settings.otp_resend_cooldown if hasattr(settings, "otp_resend_cooldown") else 60
        self.max_attempts = settings.max_otp_attempts if hasattr(settings, "max_otp_attempts") else 5

    def _make_key(self, temp_session_id: str) -> str:
        return f"{self.PREFIX}{temp_session_id}"

    def _resend_key(self, temp_session_id: str) -> str:
        return f"{self.RESEND_PREFIX}{temp_session_id}"

    def _attempt_key(self, temp_session_id: str) -> str:
        return f"{self.ATTEMPT_PREFIX}{temp_session_id}"

    def _generate_code(self) -> str:
        # numeric code of configured length
        max_val = 10 ** self.length
        n = secrets.randbelow(max_val)
        return str(n).zfill(self.length)

    def _hash(self, code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    async def create_and_send(self, temp_session_id: str, to_email: str) -> bool:
        """Generate OTP, store hash in Redis and send by email. Returns True on queued/sent."""
        key = self._make_key(temp_session_id)
        resend_key = self._resend_key(temp_session_id)

        # Check resend cooldown
        if await redis_client.conn.get(resend_key):
            # Cooldown active
            logger.info("otp_resend_blocked", extra={"temp_session_id": temp_session_id})
            return False

        code = self._generate_code()
        code_hash = self._hash(code)

        # Store hashed code + metadata as a simple string: code_hash
        # Key TTL controls expiration
        await redis_client.conn.setex(key, timedelta(seconds=self.ttl), code_hash)

        # Set resend cooldown flag
        await redis_client.conn.setex(resend_key, timedelta(seconds=self.resend_cooldown), "1")

        # Reset attempts counter
        await redis_client.conn.delete(self._attempt_key(temp_session_id))

        # Send email (fire-and-forget style)
        subject = f"Tu código de verificación - Mi Mascota"
        html = f"<p>Tu código OTP es: <strong>{code}</strong></p><p>Expira en {int(self.ttl/60)} minutos.</p>"
        text = f"Tu código OTP es: {code} - expira en {int(self.ttl/60)} minutos."

        sent = await email_service.send_email(to_email, subject, html, text)
        if sent:
            logger.info("otp_sent", extra={"temp_session_id": temp_session_id, "email": to_email})
        else:
            logger.error("otp_send_failed", extra={"temp_session_id": temp_session_id, "email": to_email})

        return sent

    async def can_resend(self, temp_session_id: str) -> bool:
        return not bool(await redis_client.conn.get(self._resend_key(temp_session_id)))

    async def validate(self, temp_session_id: str, code: str) -> bool:
        """Validate given code for temp_session_id. Returns True if valid. Invalidate on success."""
        key = self._make_key(temp_session_id)
        attempt_key = self._attempt_key(temp_session_id)

        stored = await redis_client.conn.get(key)
        if not stored:
            return False

        # attempts check
        attempts = await redis_client.conn.incr(attempt_key)
        if attempts == 1:
            await redis_client.conn.expire(attempt_key, self.ttl)

        if attempts > self.max_attempts:
            # delete code to force re-login
            await redis_client.conn.delete(key)
            await redis_client.conn.delete(attempt_key)
            logger.warning("otp_max_attempts_exceeded", extra={"temp_session_id": temp_session_id})
            return False

        code_hash = self._hash(code)
        if secrets.compare_digest(code_hash, stored):
            # success: invalidate code and attempts
            await redis_client.conn.delete(key)
            await redis_client.conn.delete(attempt_key)
            await redis_client.conn.delete(self._resend_key(temp_session_id))
            logger.info("otp_validated", extra={"temp_session_id": temp_session_id})
            return True

        return False


otp_service = OTPService()
