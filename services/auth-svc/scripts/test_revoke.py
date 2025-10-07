"""
Script de prueba directo para el método revoke
"""
import asyncio
from datetime import datetime, timezone
from app.db.base import SessionLocal
from app.db.repositories import UserSessionRepo
from app.db.models import UserSession
from sqlalchemy import select

async def test_revoke():
    # Obtener la última sesión
    async with SessionLocal() as session:
        result = await session.execute(
            select(UserSession).order_by(UserSession.created_at.desc()).limit(1)
        )
        user_session = result.scalar_one_or_none()
        
        if not user_session:
            print("❌ No hay sesiones en la BD")
            return
        
        session_id = user_session.id
        print(f"Session ID a revocar: {session_id}")
        print(f"Estado ANTES: revoked_at = {user_session.revoked_at}")
    
    # Revocar usando el repositorio
    async with SessionLocal() as session:
        repo = UserSessionRepo(session)
        await repo.revoke(str(session_id))
        print("✅ Revoke ejecutado")
    
    # Verificar
    async with SessionLocal() as session:
        result = await session.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        user_session = result.scalar_one_or_none()
        
        print(f"Estado DESPUÉS: revoked_at = {user_session.revoked_at}")
        
        if user_session.revoked_at:
            print("✅ ¡ÉXITO! La sesión fue revocada correctamente")
        else:
            print("❌ ERROR: La sesión NO fue revocada")

if __name__ == "__main__":
    asyncio.run(test_revoke())
