from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import Base, get_db
from app.main import app

# Pytest only picks up fixtures from conftest.py files. Fixtures defined in other
# modules (like tests/seeds.py) are invisible unless we register them here.
# A plain `import tests.seeds` won't work — pytest_plugins is the way to do it.
pytest_plugins = ["tests.seeds"]

# Separate Postgres database for tests — created by docker/init-test-db.sql on first startup
TEST_DATABASE_URL = "postgresql+asyncpg://super@localhost:5432/super_test"

engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
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
