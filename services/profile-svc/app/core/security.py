from base64 import b64decode
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import settings
import httpx

_security = HTTPBearer(auto_error=False)


class AuthUser:
    def __init__(self, user_id: str, roles: list[str] | None = None):
        self.user_id = user_id
        self.roles = roles or []


def _decode_rs256(token: str) -> dict | None:
    """Si hay PUBLIC KEY en base64, intenta validación RS256 real."""
    if not settings.JWT_PUBLIC_KEY_BASE64:
        return None
    try:
        pubkey_pem = b64decode(settings.JWT_PUBLIC_KEY_BASE64).decode("utf-8")
        return jwt.decode(
            token,
            pubkey_pem,
            algorithms=["RS256"],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            options={"verify_aud": settings.JWT_AUDIENCE is not None},
        )
    except Exception:
        return None


async def _introspect(token: str) -> dict | None:
    """Introspección opcional vía auth-svc si configuraste endpoint y token de servicio."""
    if not (settings.AUTH_INTROSPECTION_URL and settings.AUTH_INTROSPECTION_TOKEN):
        return None
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            r = await client.post(
                settings.AUTH_INTROSPECTION_URL,
                headers={"Authorization": f"Bearer {settings.AUTH_INTROSPECTION_TOKEN.get_secret_value()}"},
                json={"token": token},
            )
        if r.status_code == 200:
            data = r.json()
            if data.get("active"):
                return data
    except Exception:
        pass
    return None


async def get_current_user(
    token: HTTPAuthorizationCredentials = Depends(_security),
) -> AuthUser:
    if token is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    raw = token.credentials

    # 1) Preferí validación RS256 real si hay clave pública
    claims = _decode_rs256(raw)
    # 2) Si falla/ausente, probá introspección remota
    if claims is None:
        claims = await _introspect(raw)
    # 3) Fallback: leer claims sin verificar firma (dev)
    if claims is None:
        try:
            claims = jwt.get_unverified_claims(raw)
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Validaciones livianas en dev
        if settings.JWT_ISSUER and claims.get("iss") != settings.JWT_ISSUER:
            raise HTTPException(status_code=401, detail="Invalid issuer")
        if settings.JWT_AUDIENCE:
            aud = claims.get("aud")
            if isinstance(aud, str):
                ok = aud == settings.JWT_AUDIENCE
            elif isinstance(aud, list):
                ok = settings.JWT_AUDIENCE in aud
            else:
                ok = False
            if not ok:
                raise HTTPException(status_code=401, detail="Invalid audience")

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing sub")
    roles = claims.get("roles", [])
    return AuthUser(user_id=user_id, roles=roles)
