from fastapi import APIRouter, Depends, HTTPException, status, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.profile import Profile
from app.schemas.profile import ProfileOut
from app.core.metrics import profile_write_counter
from app.core.config import settings
from app.core.storage import store_profile_photo, delete_profile_photo
import re

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/profiles", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
async def create_profile_internal(payload: dict, db: AsyncSession = Depends(get_session)):
    """Internal endpoint used by auth-svc to ensure a Profile exists immediately after user registration.

    Expected payload: { "user_id": "<uuid>", "email": "...", "display_name": "..." }
    This endpoint is intended for internal network calls from the auth service and does not
    require authentication. It's resilient to existing records (will upsert when possible).
    """
    user_id = payload.get("user_id")
    email = payload.get("email")
    display_name = payload.get("display_name") or (email or "")

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    # If profile exists by user_id, update email/display_name
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    obj = result.scalar_one_or_none()

    if obj:
        obj.display_name = display_name or obj.display_name
        obj.email = email or obj.email
        try:
            await db.flush()
            await db.commit()
            profile_write_counter.labels(action="update", outcome="success").inc()
            await db.refresh(obj)
            return ProfileOut.model_validate(obj)
        except Exception:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update profile")

    # Try create
    new = Profile(user_id=user_id, display_name=display_name, email=email, services={})
    db.add(new)
    try:
        await db.flush()
        await db.commit()
        try:
            profile_write_counter.labels(action="create", outcome="success").inc()
        except Exception:
            pass
        await db.refresh(new)
        return ProfileOut.model_validate(new)
    except IntegrityError:
        await db.rollback()
        # attempt upsert by email if unique constraint prevents insert
        try:
            r2 = await db.execute(select(Profile).where(Profile.email == email))
            existing = r2.scalar_one_or_none()
            if existing:
                existing.user_id = existing.user_id or user_id
                existing.display_name = existing.display_name or display_name
                await db.flush()
                await db.commit()
                await db.refresh(existing)
                return ProfileOut.model_validate(existing)
        except Exception:
            await db.rollback()
        raise HTTPException(status_code=409, detail="Profile already exists")
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create profile")


def _sanitize_user_slug(value: str) -> str:
    return re.sub(r'[^a-z0-9_-]', '-', str(value).lower()).strip('-') or 'profile'


def _extract_object_key(photo_url: str | None) -> str | None:
    if not photo_url:
        return None
    if settings.MINIO_PUBLIC_URL:
        base = settings.MINIO_PUBLIC_URL.rstrip('/') + '/'
        if photo_url.startswith(base):
            return photo_url[len(base):]

    endpoint_prefix = (('https' if settings.MINIO_SECURE else 'http') + '://' + settings.MINIO_ENDPOINT.rstrip('/') + '/' + settings.MINIO_BUCKET + '/')
    if photo_url.startswith(endpoint_prefix):
        return photo_url[len(endpoint_prefix):]
    return None


@router.post("/profiles/{user_id}/photo", response_model=ProfileOut)
async def upload_profile_photo_internal(user_id: str, file: UploadFile = None, db: AsyncSession = Depends(get_session)):
    """Internal multipart endpoint to upload a profile photo given a user_id.

    This endpoint is intended to be called from auth-svc (service-to-service) so it
    does not require normal user authentication.
    """
    from fastapi import UploadFile
    from app.core.config import settings
    from app.core.storage import store_profile_photo, delete_profile_photo

    if not settings.MINIO_ENABLED:
        raise HTTPException(status_code=503, detail="Media storage is not configured")

    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    obj = result.scalar_one_or_none()
    if not obj:
        # try create minimal profile
        new = Profile(user_id=user_id, display_name="", email=None, services={})
        db.add(new)
        try:
            await db.flush()
            await db.commit()
            await db.refresh(new)
            obj = new
        except Exception:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to create profile for photo upload")

    if not file:
        raise HTTPException(status_code=400, detail="file is required")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    previous_snapshot = {"photo_url": obj.photo_url} if obj else {}

    try:
        object_prefix = f"profiles/{_sanitize_user_slug(obj.user_id)}/profile"
        photo_url = await store_profile_photo(
            obj.id,
            data,
            filename=file.filename,
            content_type=file.content_type,
            object_prefix=object_prefix,
        )
        obj.photo_url = photo_url
        await db.flush()
        await db.commit()
    except RuntimeError as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=502, detail="Failed to store media")

    previous_key = _extract_object_key(previous_snapshot.get("photo_url") if previous_snapshot else None)

    await db.refresh(obj)

    # Delete previous file if different
    if previous_key and previous_key != _extract_object_key(photo_url):
        try:
            await delete_profile_photo(previous_key)
        except Exception:
            pass

    return ProfileOut.model_validate(obj)
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.profile import Profile


@router.post("/profiles/verify", status_code=status.HTTP_200_OK)
async def internal_verify_profile(payload: dict, db: AsyncSession = Depends(get_session)):
    """Internal endpoint used by auth-svc to sync email verification state.

    Expected payload: {"user_id": "...", "email": "..."}
    This endpoint will set a lightweight flag inside the `services` JSON of the profile
    (services.email_verified = true). If no profile exists for the user_id, a minimal
    profile record will be created.
    """
    user_id = payload.get("user_id")
    email = payload.get("email")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")

    # Try to find existing profile
    result = await db.execute(select(Profile).where(Profile.user_id == user_id))
    obj = result.scalar_one_or_none()

    if obj:
        # ensure services dict exists
        services = obj.services or {}
        services["email_verified"] = True
        obj.services = services
        try:
            await db.flush()
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update profile")
        return {"ok": True, "updated": True}

    # If not exists, create a minimal profile entry
    try:
        new = Profile(user_id=user_id, display_name=email or "", email=email, services={"email_verified": True})
        db.add(new)
        await db.flush()
        await db.commit()
    except IntegrityError:
        await db.rollback()
        # Might happen due to race; treat as ok
        return {"ok": True, "updated": False}

    return {"ok": True, "created": True}
