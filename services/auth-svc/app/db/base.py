# services/auth-svc/app/db/base.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

# IMPORTANTE: DATABASE_URL debe ser async, ej:
# postgresql+asyncpg://app:app@localhost:5432/appdb
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
