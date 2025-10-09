from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.security import AuthUser, get_current_user
from app.db.base import Base
from app.db.session import get_session
from app.main import app as fastapi_app
from app.models.profile import Profile

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_profiles.db"

CURRENT_USER = {"id": f"user-{uuid4()}"}


@pytest.fixture(scope="session")
async def app() -> AsyncGenerator[FastAPI, None]:
    yield fastapi_app


@pytest.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

    if engine.url.get_backend_name() == "sqlite":
        for table in Base.metadata.tables.values():
            table.schema = None

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
    Path("test_profiles.db").unlink(missing_ok=True)


@pytest.fixture()
async def client(app: FastAPI, db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _get_session_override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _get_current_user_override() -> AuthUser:
        return AuthUser(user_id=CURRENT_USER["id"])

    app.dependency_overrides[get_session] = _get_session_override
    app.dependency_overrides[get_current_user] = _get_current_user_override

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    CURRENT_USER["id"] = f"user-{uuid4()}"


@pytest.fixture()
async def sample_profile(db_session: AsyncSession) -> Profile:
    profile = Profile(
        user_id=f"user-{uuid4()}",
        role="client",
        display_name="Test User",
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)
    return profile


@pytest.fixture(autouse=True)
def kafka_event_spy(monkeypatch):
    calls: list[dict[str, object]] = []

    async def _fake_send_event(topic: str, key: str | None, value: dict[str, object], **kwargs):
        calls.append({"topic": topic, "key": key, "value": value})

    monkeypatch.setattr("app.routers.profiles.send_event", _fake_send_event)
    return calls


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
def set_current_user():
    original = CURRENT_USER["id"]

    def _setter(user_id: str) -> str:
        CURRENT_USER["id"] = user_id
        return user_id

    yield _setter
    CURRENT_USER["id"] = original
