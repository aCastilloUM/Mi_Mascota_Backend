import asyncio
from app.db.base import SessionLocal
from app.db.models import UserSession
from sqlalchemy import select

async def check():
    async with SessionLocal() as s:
        r = await s.execute(select(UserSession).where(UserSession.id == 'efaecdfb-dbc5-472d-b1e6-b77550b100f2'))
        sess = r.scalar_one_or_none()
        print(f'Revoked: {sess.revoked_at if sess else "No encontrada"}')

asyncio.run(check())
