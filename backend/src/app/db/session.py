from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Naming conventions for database constraints.
# Without these, Alembic can't autogenerate consistent constraint names across migrations.
# This is equivalent to Rails' automatic constraint naming.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",  # Index
    "uq": "uq_%(table_name)s_%(column_0_name)s",  # Unique constraint
    "ck": "ck_%(table_name)s_%(constraint_name)s",  # Check constraint
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",  # Foreign key
    "pk": "pk_%(table_name)s",  # Primary key
}


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    All models inherit from this class. SQLAlchemy uses Base.metadata to track
    all registered models and their table schemas.

    The naming_convention ensures all constraints have predictable names,
    which is critical for Alembic migrations to work correctly.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Async engine with connection pooling.
# The engine manages a pool of database connections that are reused across requests.
engine = create_async_engine(
    settings.database_url,
    # Pool configuration — see docs/database.md for detailed explanation
    pool_size=settings.db_pool_size,  # Persistent connections
    max_overflow=settings.db_max_overflow,  # Extra connections under load
    pool_timeout=settings.db_pool_timeout,  # Wait time for available connection
    pool_recycle=settings.db_pool_recycle,  # Max connection age (prevents stale connections)
    pool_pre_ping=settings.db_pool_pre_ping,  # Test connection before checkout
    echo=settings.db_echo,  # SQL logging
    # asyncpg driver options — passed directly to asyncpg.connect()
    connect_args={"command_timeout": settings.db_statement_timeout},  # Kill slow queries
)

# Session factory — creates AsyncSession instances.
# expire_on_commit=False keeps objects usable after commit without re-querying.
# This is important for async because accessing expired attributes would trigger sync I/O.
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides a database session per request.

    Commits on success, rolls back on exception. This is the single place where
    transaction boundaries are managed — services and repositories never call
    commit() or rollback() directly.

    Usage in endpoints:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def shutdown() -> None:
    """Graceful shutdown — close all pooled database connections.

    Call this in FastAPI's lifespan context manager on shutdown.
    Ensures connections are properly closed before the process exits.
    """
    await engine.dispose()
