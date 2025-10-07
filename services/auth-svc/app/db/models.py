# app/db/models.py
from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import (
    String, DateTime, ForeignKey, Enum as SAEnum, text
)
from app.core.config import settings


class Base(DeclarativeBase):
    pass


# ENUM en Postgres: auth.user_status_enum ('active','pending','blocked')
UserStatusEnum = SAEnum(
    "active", "pending", "blocked",
    name="user_status_enum",
    schema=settings.db_schema,   # "auth"
    native_enum=True,
    create_type=False,           # el tipo ya lo crea Alembic
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": settings.db_schema}  # "auth"

    # Dejar que Postgres genere el UUID (gen_random_uuid())
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Usa el ENUM real en DB
    status: Mapped[str] = mapped_column(
        UserStatusEnum,
        nullable=False,
        server_default=text("'active'::text"),  # default igual que en la migración
    )

    full_name: Mapped[str | None] = mapped_column(String(255))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Email verification
    email_verified: Mapped[bool] = mapped_column(
        nullable=False,
        server_default=text("false")
    )
    email_verification_token: Mapped[str | None] = mapped_column(String(255), index=True)
    email_verification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Password reset
    password_reset_token: Mapped[str | None] = mapped_column(String(255), index=True)
    password_reset_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Account locking
    failed_login_attempts: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # 2FA TOTP
    two_factor_enabled: Mapped[bool] = mapped_column(
        nullable=False,
        server_default=text("false"),
        index=True
    )
    two_factor_secret: Mapped[str | None] = mapped_column(String(32))
    two_factor_backup_codes: Mapped[list[str] | None] = mapped_column(
        ARRAY(String)
    )
    two_factor_enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
        onupdate=datetime.utcnow,  # refresca desde ORM; en DB queda el server_default inicial
    )


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = {"schema": settings.db_schema}  # "auth"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey(f"{settings.db_schema}.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512))
    ip: Mapped[str | None] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
