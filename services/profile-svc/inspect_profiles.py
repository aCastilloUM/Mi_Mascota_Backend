import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.profile import Profile

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Profile))
        for p in result.scalars():
            print(p.id, p.user_id, p.display_name)

asyncio.run(main())
