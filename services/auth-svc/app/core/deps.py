from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.base import get_session
from typing import AsyncGenerator
from app.db.base import SessionLocal  # tu async_sessionmaker

DbSession = Annotated[AsyncSession, Depends(get_session)]

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session