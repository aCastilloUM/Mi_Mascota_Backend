from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.profile import ProfileRole


class ProfileBase(BaseModel):
    """Shared fields reused across create/update/output; optional types ease partial updates."""

    display_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    role: Optional[ProfileRole] = None
    bio: Optional[str] = Field(default=None, max_length=500)
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    services: Optional[dict[str, Any]] = None
    photo_url: Optional[str] = None

    name: Optional[str] = Field(default=None, max_length=100)
    second_name: Optional[str] = Field(default=None, max_length=100)
    email: Optional[EmailStr] = None
    document_type: Optional[str] = Field(default=None, max_length=20)
    document: Optional[str] = Field(default=None, max_length=50)

    department: Optional[str] = Field(default=None, max_length=100)
    postal_code: Optional[str] = Field(default=None, max_length=20)
    street: Optional[str] = Field(default=None, max_length=120)
    number: Optional[str] = Field(default=None, max_length=20)
    apartment: Optional[str] = Field(default=None, max_length=20)

    birth_date: Optional[date] = None

    @field_validator("latitude")
    @classmethod
    def _lat_range(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not (-90 <= value <= 90):
            raise ValueError("latitude fuera de rango")
        return value

    @field_validator("longitude")
    @classmethod
    def _lon_range(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not (-180 <= value <= 180):
            raise ValueError("longitude fuera de rango")
        return value


class ProfileCreate(ProfileBase):
    role: ProfileRole = Field(default=ProfileRole.client)
    display_name: str = Field(..., min_length=2, max_length=100)


class ProfileUpdate(ProfileBase):
    pass


class ProfileOut(ProfileBase):
    id: UUID
    user_id: str
    role: ProfileRole
    display_name: str
    rating: Optional[float] = None
    rating_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProfileHistoryOut(BaseModel):
    history_id: UUID
    profile_id: UUID
    change_type: str
    changed_by: Optional[str] = None
    change_origin: Optional[str] = None
    change_reason: Optional[str] = None
    snapshot: Optional[dict[str, Any]] = None
    previous_snapshot: Optional[dict[str, Any]] = None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)
