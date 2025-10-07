from logging.config import fileConfig
from sqlalchemy import create_engine
from alembic import context

from app.db.models import Base
from app.core.config import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name) 

target_metadata = Base.metadata

def _sync_url() -> str:
    return settings.database_url.replace("+asyncpg", "")

def run_migrations_offline() -> None:
    context.configure(
        url=_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = create_engine(_sync_url())
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
