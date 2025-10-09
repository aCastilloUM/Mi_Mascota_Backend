# app/db/migrations/env.py
import os
import asyncio
from logging.config import fileConfig
from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from pathlib import Path
import sys

# --- FIX para que Python encuentre el paquete "app" ---
ROOT_DIR = Path(__file__).resolve().parents[3]  # sube hasta services/profile-svc
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))   

from app.db.base import Base
import app.models.profile
from app.core.config import settings



# Config Alembic (logs)
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def _async_url() -> str:
    # Permite override desde el host (Windows) cuando el .env usa DB_HOST=postgres (solo válido dentro de Docker)
    return os.getenv("ALEMBIC_DATABASE_URL") or settings.database_url  # ej: postgresql+asyncpg://...

def run_migrations_offline() -> None:
    """Modo offline sigue siendo sync (genera SQL sin conectar)."""
    url = _async_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    """Configura el contexto ya dentro de una conexión sync (bridge)."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Modo online asincrónico con asyncpg."""
    connectable: AsyncEngine = create_async_engine(_async_url(), pool_pre_ping=True, connect_args={"server_settings": {"search_path": f"{settings.DB_SCHEMA},public"}})

    async with connectable.connect() as async_conn:
        # Alembic espera una conexión “sync”. Bridge con run_sync:
        await async_conn.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
