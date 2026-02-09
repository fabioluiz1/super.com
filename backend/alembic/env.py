"""Alembic environment configuration for async SQLAlchemy.

This file runs when you execute alembic commands. It configures the database
connection and tells Alembic which models to track for autogenerate.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import our app's Base (contains all model metadata) and settings (database URL)
import app.models  # noqa: F401 — registers models with Base.metadata for autogenerate
from app.config import settings
from app.db.session import Base

# Alembic Config object — provides access to alembic.ini values
config = context.config

# Override sqlalchemy.url from alembic.ini with our app's DATABASE_URL
# This ensures migrations use the same database as the app
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up Python logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic which models to track for --autogenerate
# Base.metadata contains all tables from models that inherit from Base
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — generates SQL without connecting.

    Useful for reviewing migration SQL before applying, or for environments
    where you can't connect directly to the database.

    Usage: alembic upgrade head --sql > migration.sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Execute migrations within a transaction."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create async engine and run migrations.

    Uses NullPool because migrations are a one-shot operation —
    we don't need connection pooling for a single migration run.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — connects to database and applies."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
