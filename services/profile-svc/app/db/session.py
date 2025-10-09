# app/db/session.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings

# --- Engine ---
engine = create_async_engine(
    settings.database_url,
    echo=settings.DB_ECHO,
    pool_pre_ping=True,           # chequea conexión antes de usar
    pool_size=settings.DB_POOL_SIZE,
    connect_args={"server_settings": {"search_path": f"{settings.DB_SCHEMA},public"}},
)

# --- Session factory ---
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,       # no expira objetos al hacer commit
    autoflush=False,
)

# --- Dependency FastAPI ---
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency para inyectar un AsyncSession en endpoints.
    Cierra automáticamente después del uso.
    """
    async with AsyncSessionLocal() as session:
        yield session
