"""
Script para verificar el estado de las sesiones en la BD
"""
import asyncio
from app.db.base import SessionLocal
from app.db.models import UserSession
from sqlalchemy import select

async def check_sessions():
    async with SessionLocal() as session:
        result = await session.execute(
            select(UserSession).order_by(UserSession.created_at.desc()).limit(5)
        )
        sessions = result.scalars().all()
        
        print("\n" + "="*80)
        print("ÚLTIMAS 5 SESIONES EN LA BASE DE DATOS")
        print("="*80)
        
        for sess in sessions:
            print(f"\nSession ID: {sess.id}")
            print(f"  User ID: {sess.user_id}")
            print(f"  Created: {sess.created_at}")
            print(f"  Expires: {sess.expires_at}")
            print(f"  Revoked: {sess.revoked_at}")
            print(f"  Status: {'REVOCADA' if sess.revoked_at else 'ACTIVA'}")

if __name__ == "__main__":
    asyncio.run(check_sessions())
