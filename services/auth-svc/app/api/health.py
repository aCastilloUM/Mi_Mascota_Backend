# app/api/health.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_session

router = APIRouter(tags=["ops"])

@router.get("/health")
async def health():
    return {"ok": True}

@router.get("/ready")
async def ready(session: AsyncSession = Depends(get_session)):
    try:
        await session.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        raise HTTPException(status_code=503, detail="db not ready")
