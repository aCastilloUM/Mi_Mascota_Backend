"""
Test directo del endpoint logout con logging
"""
import requests

BASE_URL = "http://localhost:8002/api/v1/auth"

# Login primero
print("1. Login...")
session = requests.Session()
login_resp = session.post(f"{BASE_URL}/login", json={
    "email": "juan.perez@test.com",
    "password": "TestPass123!"
})

if login_resp.status_code != 200:
    print(f"Login falló: {login_resp.status_code}")
    exit(1)

refresh_cookie = session.cookies.get('refresh_token')
print(f"Cookie obtenida: {refresh_cookie[:50]}...")

# Logout
print("\n2. Logout...")
logout_resp = session.post(f"{BASE_URL}/logout")
print(f"Status: {logout_resp.status_code}")
print(f"Response: {logout_resp.json()}")

# Verificar en BD
print("\n3. Verificando en BD...")
import asyncio
import sys
sys.path.insert(0, '..')
from app.db.base import SessionLocal
from app.db.models import UserSession
from sqlalchemy import select

async def check_db():
    session_id = refresh_cookie.split('.')[0]
    async with SessionLocal() as s:
        r = await s.execute(select(UserSession).where(UserSession.id == session_id))
        sess = r.scalar_one_or_none()
        if sess:
            print(f"Session ID: {sess.id}")
            print(f"Revoked: {sess.revoked_at}")
            if sess.revoked_at:
                print("✅ Sesión REVOCADA correctamente")
            else:
                print("❌ Sesión NO revocada")
        else:
            print("❌ Sesión no encontrada")

asyncio.run(check_db())
