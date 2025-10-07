import asyncio
from app.db.base import SessionLocal
from app.db.models import UserSession
from sqlalchemy import select

async def check_types():
    async with SessionLocal() as s:
        r = await s.execute(select(UserSession).limit(1))
        sess = r.scalar_one_or_none()
        if sess:
            print(f"ID value: {sess.id}")
            print(f"ID type: {type(sess.id)}")
            print(f"ID repr: {repr(sess.id)}")

asyncio.run(check_types())
