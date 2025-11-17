import logging
import re
from time import perf_counter
from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Response, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.kafka import send_event
from app.core.metrics import (
    profile_history_counter,
    profile_photo_upload_duration,
    profile_photo_upload_total,
    profile_write_counter,
)
from app.core.security import AuthUser, get_current_user
from app.core.storage import delete_profile_photo, store_profile_photo
from app.db.session import get_session
from app.models.profile import Profile, ProfileHistory
from app.schemas.profile import ProfileCreate, ProfileHistoryOut, ProfileOut, ProfileUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["profiles"])

def _sanitize_user_slug(value: str) -> str:
    return re.sub(r'[^a-z0-9_-]', '-', value.lower()).strip('-') or 'profile'



def _extract_object_key(photo_url: Optional[str]) -> Optional[str]:
    if not photo_url:
        return None

    if settings.MINIO_PUBLIC_URL:
        base = settings.MINIO_PUBLIC_URL.rstrip("/") + "/"
        if photo_url.startswith(base):
            return photo_url[len(base) :]

    endpoint_prefix = (
        ("https" if settings.MINIO_SECURE else "http")
        + "://"
        + settings.MINIO_ENDPOINT.rstrip("/")
        + "/"
        + settings.MINIO_BUCKET
        + "/"
    )
    if photo_url.startswith(endpoint_prefix):
        return photo_url[len(endpoint_prefix) :]

    return None



def _profile_snapshot(obj: Profile) -> dict:
    snapshot: dict[str, Any] = {}
    for key, value in obj.__dict__.items():
        if key.startswith("_sa_"):
            continue
        snapshot[key] = _coerce_serializable(value)
    return snapshot


def _coerce_serializable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


async def _record_history(
    db: AsyncSession,
    *,
    profile_id: UUID,
    change_type: str,
    snapshot: dict | None,
    previous_snapshot: dict | None,
    changed_by: str | None = None,
    change_origin: str = "api",
    change_reason: str | None = None,
) -> None:
    history = ProfileHistory(
        history_id=uuid4(),
        profile_id=profile_id,
        change_type=change_type,
        changed_by=changed_by,
        change_origin=change_origin,
        change_reason=change_reason,
        snapshot=snapshot,
        previous_snapshot=previous_snapshot,
    )
    db.add(history)
    profile_history_counter.labels(action=change_type).inc()

@router.get("", response_model=Page[ProfileOut])
async def list_profiles(db: AsyncSession = Depends(get_session)):
    query = select(Profile).order_by(Profile.created_at.desc())
    return await paginate(db, query)


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: ProfileCreate,
    response: Response,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    user_id = current_user.user_id

    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    existing = result.scalar_one_or_none()

    if payload.email:
        email_result = await db.execute(select(Profile).where(Profile.email == payload.email))
        email_owner = email_result.scalar_one_or_none()
        if email_owner and (not existing or email_owner.id != existing.id):
            raise HTTPException(status_code=409, detail="Profile already exists (user_id/email/document)")

    if existing:
        change_type = "update"
        profile_write_counter.labels(action=change_type, outcome="attempt").inc()
        previous_snapshot = _profile_snapshot(existing)
        for key, value in data.items():
            setattr(existing, key, value)
        obj = existing
        is_new = False
        response.status_code = status.HTTP_200_OK
    else:
        change_type = "create"
        profile_write_counter.labels(action=change_type, outcome="attempt").inc()
        obj = Profile(user_id=user_id, **data)
        db.add(obj)
        previous_snapshot = None
        is_new = True

    try:
        await db.flush()
        await _record_history(
            db,
            profile_id=obj.id,
            change_type=change_type,
            snapshot=_profile_snapshot(obj),
            previous_snapshot=previous_snapshot,
            changed_by=user_id,
        )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        profile_write_counter.labels(action=change_type, outcome="failure").inc()
        raise HTTPException(status_code=409, detail="Profile already exists (user_id/email/document)") from exc
    except DataError as exc:
        await db.rollback()
        profile_write_counter.labels(action=change_type, outcome="failure").inc()
        raise HTTPException(status_code=400, detail="Invalid data for profile") from exc
    else:
        profile_write_counter.labels(action=change_type, outcome="success").inc()

    await db.refresh(obj)

    event_payload = {
        "event": "client_registered",
        "version": 1,
        "profile_id": str(obj.id),
        "user_id": obj.user_id,
        "role": obj.role,
        "display_name": obj.display_name,
        "bio": obj.bio,
        "city": obj.city,
        "latitude": obj.latitude,
        "longitude": obj.longitude,
        "services": obj.services or {},
        "photo_url": obj.photo_url,
        "email": obj.email,
        "document_type": obj.document_type,
        "document": obj.document,
        "department": obj.department,
        "postal_code": obj.postal_code,
        "street": obj.street,
        "number": obj.number,
        "apartment": obj.apartment,
        "birth_date": obj.birth_date.isoformat() if obj.birth_date else None,
        "occurred_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "is_new": is_new,
    }

    try:
        await send_event(
            settings.KAFKA_TOPIC_PROFILE_REGISTERED,
            key=str(obj.id),
            value=event_payload,
        )
    except Exception:
        logger.exception("Failed to publish Kafka event profiles.client.registered.v1")

    return ProfileOut.model_validate(obj)


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(db: AsyncSession = Depends(get_session), current_user: AuthUser = Depends(get_current_user)):
    """Return the profile associated with the currently authenticated user."""
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.user_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileOut.model_validate(obj)


@router.get("/{profile_id}", response_model=ProfileOut)
async def get_profile(profile_id: UUID, db: AsyncSession = Depends(get_session)):
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileOut.model_validate(obj)


@router.put("/{profile_id}", response_model=ProfileOut)
async def update_profile(
    profile_id: UUID,
    payload: ProfileUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
):
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Profile not found")

    if obj.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    profile_write_counter.labels(action="update", outcome="attempt").inc()
    previous_snapshot = _profile_snapshot(obj)
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(obj, key, value)

    try:
        await db.flush()
        await _record_history(
            db,
            profile_id=obj.id,
            change_type="update",
            snapshot=_profile_snapshot(obj),
            previous_snapshot=previous_snapshot,
            changed_by=current_user.user_id,
        )
        await db.commit()
    except (IntegrityError, DataError) as exc:
        await db.rollback()
        profile_write_counter.labels(action="update", outcome="failure").inc()
        if isinstance(exc, IntegrityError):
            raise HTTPException(status_code=409, detail="Profile already exists (user_id/email/document)") from exc
        raise HTTPException(status_code=400, detail="Invalid data for profile") from exc
    else:
        profile_write_counter.labels(action="update", outcome="success").inc()

    await db.refresh(obj)
    return ProfileOut.model_validate(obj)


@router.post("/{profile_id}/photo", response_model=ProfileOut)
async def upload_profile_photo(
    profile_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
):
    if not settings.MINIO_ENABLED:
        raise HTTPException(status_code=503, detail="Media storage is not configured")

    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Profile not found")

    if obj.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    profile_photo_upload_total.labels(outcome="attempt").inc()
    start = perf_counter()
    previous_snapshot = _profile_snapshot(obj)

    slug = _sanitize_user_slug(obj.user_id)
    object_prefix = f"profiles/{slug}/profile"

    try:
        photo_url = await store_profile_photo(
            profile_id,
            data,
            filename=file.filename,
            content_type=file.content_type,
            object_prefix=object_prefix,
        )
        obj.photo_url = photo_url
        await db.flush()
        await _record_history(
            db,
            profile_id=obj.id,
            change_type="update",
            snapshot=_profile_snapshot(obj),
            previous_snapshot=previous_snapshot,
            changed_by=current_user.user_id,
            change_reason="photo_upload",
        )
        await db.commit()
    except RuntimeError as exc:
        await db.rollback()
        profile_photo_upload_total.labels(outcome="failure").inc()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        profile_photo_upload_total.labels(outcome="failure").inc()
        logger.exception("Failed to upload photo to MinIO")
        raise HTTPException(status_code=502, detail="Failed to store media") from exc
    else:
        profile_photo_upload_total.labels(outcome="success").inc()
        profile_photo_upload_duration.observe(perf_counter() - start)

    previous_key = _extract_object_key(previous_snapshot.get("photo_url") if previous_snapshot else None)

    await db.refresh(obj)

    if previous_key and previous_key != _extract_object_key(photo_url):
        try:
            await delete_profile_photo(previous_key)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to delete previous profile photo %s", previous_key, exc_info=True)

    return ProfileOut.model_validate(obj)


@router.get("/{profile_id}/history", response_model=Page[ProfileHistoryOut])
async def list_profile_history(
    profile_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
):
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Profile not found")
    if obj.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    query = select(ProfileHistory).where(ProfileHistory.profile_id == profile_id).order_by(ProfileHistory.changed_at.desc())
    return await paginate(db, query)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_session),
    current_user: AuthUser = Depends(get_current_user),
):
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Profile not found")

    if obj.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    profile_write_counter.labels(action="delete", outcome="attempt").inc()
    previous_snapshot = _profile_snapshot(obj)
    previous_key = _extract_object_key(obj.photo_url)
    profile_id_value = obj.id
    changed_by = current_user.user_id

    try:
        await db.delete(obj)
        await _record_history(
            db,
            profile_id=profile_id_value,
            change_type="delete",
            snapshot=None,
            previous_snapshot=previous_snapshot,
            changed_by=changed_by,
        )
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        profile_write_counter.labels(action="delete", outcome="failure").inc()
        raise exc
    else:
        profile_write_counter.labels(action="delete", outcome="success").inc()

    if previous_key:
        try:
            await delete_profile_photo(previous_key)
        except Exception:  # noqa: BLE001
            logger.warning("Failed to delete profile media %s", previous_key, exc_info=True)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


