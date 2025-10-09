import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.core.config import settings


class ProfileRole(str, Enum):
    client = "client"
    provider = "provider"


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_profile_user_id"),
        UniqueConstraint("email", name="uq_profiles_email"),
        UniqueConstraint("document", name="uq_profiles_document"),
        Index("ix_profiles_city", "city"),
        {"schema": settings.DB_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)

    role: Mapped[ProfileRole] = mapped_column(
        SAEnum(ProfileRole, name="profile_role", create_type=False, schema=settings.DB_SCHEMA),
        nullable=False,
        default=ProfileRole.client,
    )

    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bio: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(100))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    services: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    photo_url: Mapped[str | None] = mapped_column(String(300))
    rating: Mapped[float | None] = mapped_column(Float)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    name: Mapped[str | None] = mapped_column(String(100))
    second_name: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    document_type: Mapped[str | None] = mapped_column(String(20))
    document: Mapped[str | None] = mapped_column(String(50), index=True)

    department: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    street: Mapped[str | None] = mapped_column(String(120))
    number: Mapped[str | None] = mapped_column(String(20))
    apartment: Mapped[str | None] = mapped_column(String(20))
    birth_date: Mapped[Date | None] = mapped_column(Date)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )

class ProfileHistory(Base):
    __tablename__ = "profile_history"
    __table_args__ = (
        Index("ix_profile_history_profile_id", "profile_id"),
        {"schema": settings.DB_SCHEMA},
    )

    history_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(100))
    change_origin: Mapped[str | None] = mapped_column(String(50), default="api")
    change_reason: Mapped[str | None] = mapped_column(String(255))
    snapshot: Mapped[dict | None] = mapped_column(JSON)
    previous_snapshot: Mapped[dict | None] = mapped_column(JSON)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
