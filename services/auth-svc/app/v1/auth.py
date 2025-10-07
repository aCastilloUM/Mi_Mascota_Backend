# services/auth-svc/app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.services.auth_service import AuthService, InvalidRegistration
from app.api.v1.schemas import RegisterRequest, UserOut  # 👈 importa desde api/v1/schemas

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterRequest, session: AsyncSession = Depends(get_session)):
    svc = AuthService(session)
    try:
        user = await svc.register(payload)
        return UserOut(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            status=user.status,
            created_at=user.created_at,
        )
    except InvalidRegistration as e:
        raise HTTPException(status_code=400, detail=str(e))
