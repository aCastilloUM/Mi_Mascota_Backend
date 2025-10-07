"""init auth schema, users and user_sessions

Revision ID: 20250916_0001
Revises:
Create Date: 2025-09-16 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "20250916_0001"
down_revision = None
branch_labels = None
depends_on = None

AUTH_SCHEMA = "auth"


def upgrade():
    # 1) Schema
    op.execute(f'CREATE SCHEMA IF NOT EXISTS "{AUTH_SCHEMA}"')

    # 2) Extensión para UUID
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # 3) Tabla users (status TEXT + CHECK inline para evitar ALTER TABLE)
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.CheckConstraint(
            "status IN ('active','pending','blocked')",
            name="ck_auth_users_status",
        ),
        schema=AUTH_SCHEMA,
    )

    # Índice por email (nota: pasamos schema aparte)
    op.create_index(
        "ix_auth_users_email",
        table_name="users",
        columns=["email"],
        unique=True,
        schema=AUTH_SCHEMA,
    )

    # 4) Tabla user_sessions
    op.create_table(
        "user_sessions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(255), nullable=False),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("timezone('utc', now())"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        schema=AUTH_SCHEMA,
    )

    # FK entre user_sessions.user_id -> users.id (esquemas explicitados)
    op.create_foreign_key(
        "fk_user_sessions_user",
        source_table="user_sessions",
        referent_table="users",
        local_cols=["user_id"],
        remote_cols=["id"],
        source_schema=AUTH_SCHEMA,
        referent_schema=AUTH_SCHEMA,
        ondelete="CASCADE",
    )

    # Índices de user_sessions
    op.create_index(
        "ix_auth_user_sessions_user_id",
        table_name="user_sessions",
        columns=["user_id"],
        unique=False,
        schema=AUTH_SCHEMA,
    )
    op.create_index(
        "ix_auth_user_sessions_refresh_hash",
        table_name="user_sessions",
        columns=["refresh_token_hash"],
        unique=False,
        schema=AUTH_SCHEMA,
    )


def downgrade():
    op.drop_index(
        "ix_auth_user_sessions_refresh_hash",
        table_name="user_sessions",
        schema=AUTH_SCHEMA,
    )
    op.drop_index(
        "ix_auth_user_sessions_user_id",
        table_name="user_sessions",
        schema=AUTH_SCHEMA,
    )
    op.drop_constraint(
        "fk_user_sessions_user",
        "user_sessions",
        type_="foreignkey",
        schema=AUTH_SCHEMA,
    )
    op.drop_table("user_sessions", schema=AUTH_SCHEMA)

    op.drop_index("ix_auth_users_email", table_name="users", schema=AUTH_SCHEMA)
    op.drop_table("users", schema=AUTH_SCHEMA)
