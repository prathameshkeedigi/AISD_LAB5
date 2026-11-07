"""Shared fixtures: a fresh in-memory SQLite database per test, synthetic data only (NFR-4.6)."""
import os

os.environ.setdefault("TALENTHUB_SECRET_KEY", "test-secret-not-for-production")
os.environ.setdefault("TALENTHUB_BCRYPT_ROUNDS", "4")  # fast hashing for tests only

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool



@pytest_asyncio.fixture
async def engine():
    from app.models.models import Base

    eng = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)

    @event.listens_for(eng.sync_engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def seeded_db(db):
    from app.seed import seed_if_empty

    await seed_if_empty(db)
    return db


@pytest_asyncio.fixture
async def client(engine, seeded_db):
    from app.core.database import get_db
    from main import app

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_db():
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def login(client, email, password="password123"):
    r = await client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
