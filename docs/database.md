# Database

## Connection URL

`postgresql+asyncpg://super@localhost:5432/super`

| Part | Meaning |
|------|---------|
| `postgresql` | SQLAlchemy dialect name for PostgreSQL |
| `asyncpg` | Async driver (DBAPI). SQLAlchemy needs a driver to talk to the database. `asyncpg` is a high-performance async PostgreSQL driver written in Cython |
| `super@localhost:5432/super` | `user@host:port/database`. No password because Docker Compose uses trust authentication |

Alternatives: `psycopg` (sync, most popular), `psycopg[async]` (async version of psycopg3).

## SQLAlchemy Async Setup ([session.py](../backend/src/app/db/session.py))

### Engine

```python
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    ...
)
```

`create_async_engine(url)` creates a connection pool to the database. The engine doesn't connect immediately — it creates connections on demand and reuses them. Pool settings control how many concurrent connections are allowed (see [Connection Pool](#connection-pool) below).

### Session Factory

```python
async_session = async_sessionmaker(engine, expire_on_commit=False)
```

A factory that creates `AsyncSession` instances. A session is a unit-of-work: it tracks objects you've loaded/modified, and flushes changes to the database when you commit.

`expire_on_commit=False` keeps objects usable after commit without re-querying. This is important for async — accessing expired attributes would trigger a sync database call, which raises an error in async context.

### Database Dependency

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

FastAPI dependency that yields one session per request. The `async with` context manager ensures the session is closed even if the request raises an exception. This pattern (one session per request, injected via `Depends(get_db)`) is standard for FastAPI + SQLAlchemy.

### Base Model

```python
class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
```

Base class for all ORM models. Every model inherits from `Base`. SQLAlchemy uses `Base.metadata` to track all registered models and their table schemas. The `naming_convention` ensures all constraints have predictable names (see [Naming Conventions](#naming-conventions) below).

### Graceful Shutdown

```python
async def shutdown() -> None:
    await engine.dispose()
```

Closes all pooled connections. Called in FastAPI's lifespan context manager on app shutdown.

## pydantic-settings ([config.py](../backend/src/app/config.py))

```python
class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://super@localhost:5432/super"
    db_pool_size: int = 5
    ...

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

`Settings(BaseSettings)` automatically reads environment variables. Field `database_url` maps to env var `DATABASE_URL` (case-insensitive). In production, set `DATABASE_URL` in the environment. In development, the default points to Docker Compose PostgreSQL. The `env_file=".env"` also reads from a `.env` file if present.

This [12-factor](https://12factor.net/config) pattern keeps secrets out of code.

## Connection Pool

SQLAlchemy maintains a pool of database connections that are reused across requests. This avoids the overhead of establishing a new connection for every query.

### Pool Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `pool_size` | 5 | Number of persistent connections kept open. These connections are always available, even when idle. |
| `max_overflow` | 10 | Extra connections created under load, beyond `pool_size`. These are closed when no longer needed. Total max = `pool_size + max_overflow`. |
| `pool_timeout` | 30 | Seconds to wait for an available connection before raising `TimeoutError`. If all connections are busy and max_overflow is reached, new requests wait up to this long. |
| `pool_recycle` | 3600 | Recreate connections older than this (seconds). Prevents issues with stale connections that databases may close after inactivity. Set lower than your database's `wait_timeout`. |
| `pool_pre_ping` | true | Test each connection with `SELECT 1` before checkout. Catches dead connections (network issues, database restart) before your query fails. Small overhead (~1ms) but prevents cryptic errors. |
| `echo` | false | Log all SQL statements. Enable for debugging, disable in production (noisy and potential security risk). |
| `statement_timeout` | 30 | Max seconds a query can run before being killed. Prevents runaway queries from holding connections and blocking other requests. |

### Tuning for Production

**Sizing `pool_size`**: Start with `pool_size = number_of_web_workers`. Each worker needs at least one connection. If your app makes concurrent database calls within a single request (e.g., parallel queries), increase accordingly.

**Sizing `max_overflow`**: This handles traffic spikes. Set it high enough to absorb bursts without queuing requests. Monitor for `TimeoutError` exceptions — if you see them, increase `max_overflow` or `pool_size`.

**`pool_recycle` and cloud databases**: AWS RDS, Cloud SQL, and other managed databases often close idle connections after 5-10 minutes. Set `pool_recycle` lower than their timeout (e.g., 300 seconds for a 10-minute database timeout).

### Environment Variables

Configure via environment variables (see `.env.example`):

```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/dbname
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
DB_ECHO=false
DB_STATEMENT_TIMEOUT=30
```

## Naming Conventions

SQLAlchemy uses naming conventions to generate consistent constraint names. This is critical for Alembic migrations — without predictable names, Alembic can't generate `DROP CONSTRAINT` statements correctly.

The conventions follow this pattern:

| Constraint | Pattern | Example |
|------------|---------|---------|
| Primary key | `pk_%(table_name)s` | `pk_users` |
| Foreign key | `fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s` | `fk_orders_user_id_users` |
| Unique | `uq_%(table_name)s_%(column_0_name)s` | `uq_users_email` |
| Check | `ck_%(table_name)s_%(constraint_name)s` | `ck_orders_amount_positive` |
| Index | `ix_%(column_0_label)s` | `ix_users_email` |

This is equivalent to Rails' automatic constraint naming — you never need to manually name constraints, and migrations work correctly.
