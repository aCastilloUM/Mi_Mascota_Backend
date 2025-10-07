# services/auth-svc/app/core/security.py
from datetime import datetime, timedelta, timezone
import secrets
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.core.config import settings

ALG = "HS256"
ph = PasswordHasher()

# ------------ Password hashing ------------
def hash_password(plain: str) -> str:
    return ph.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    try:
        ph.verify(hashed, plain)
        return True
    except VerifyMismatchError:
        return False

# ------------ Access Token (JWT) ------------
def create_access_token(*, sub: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=settings.access_token_ttl_seconds)
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "sub": sub,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALG)

def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[ALG],
        audience=settings.jwt_audience,
        options={"require": ["exp", "iat", "iss", "sub", "aud"]},
        issuer=settings.jwt_issuer,
    )

# ------------ Refresh Token (opaco) ------------
def generate_refresh_token_raw() -> str:
    # 256 bits (~43 chars urlsafe) está muy bien
    return secrets.token_urlsafe(43)

def hash_refresh_token(raw: str) -> str:
    return ph.hash(raw)

def verify_refresh_token(raw: str, hashed: str) -> bool:
    try:
        ph.verify(hashed, raw)
        return True
    except VerifyMismatchError:
        return False

# Cookie value = "<session_id>.<raw_token>"
def build_refresh_cookie_value(session_id: str, raw_token: str) -> str:
    return f"{session_id}.{raw_token}"

def parse_refresh_cookie_value(cookie_val: str) -> tuple[str, str] | None:
    if not cookie_val or "." not in cookie_val:
        return None
    sid, raw = cookie_val.split(".", 1)
    return sid, raw
