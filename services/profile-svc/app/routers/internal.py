from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.profile import Profile

router = APIRouter(prefix="/internal", tags=["internal"])


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
