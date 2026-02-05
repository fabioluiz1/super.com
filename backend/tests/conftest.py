from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app

# SQLite async in-memory database for tests — no Docker needed, fast, isolated per test
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def db() -> AsyncIterator[AsyncSession]:
    """Create tables and yield a session, then drop tables after test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncIterator[AsyncClient]:
    """HTTP client that uses the test database session."""

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
