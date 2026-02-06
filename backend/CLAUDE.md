# Backend — Claude Code Instructions

## Python & Dependencies

- Python 3.12, pinned in `.mise.toml`
- uv for package management — `uv sync` to install, `uv run` to execute tools
- Production deps in `[project.dependencies]`, dev deps in `[dependency-groups.dev]` inside `backend/pyproject.toml`

## Code Style

- Ruff handles both linting and formatting — line-length 100, target `py312`
- mypy `strict = true` — every function must have complete type annotations (parameters + return)
- `pydantic.mypy` plugin enabled — Pydantic models are preferred over raw dicts for structured data

## FastAPI Patterns

- Async everywhere — all endpoints, dependencies, and database calls use `async/await`
- Dependency injection via `Annotated[Type, Depends(fn)]` — never call dependencies manually
- DB alias: `DB = Annotated[AsyncSession, Depends(get_db)]` in `main.py` — use it in all endpoints
- Lifespan context manager for startup/shutdown — not the deprecated `@app.on_event()`
- Global exception handler logs with request context and returns generic errors — no stack traces to clients
- Source layout: `backend/src/app/` — imports start with `app.` (e.g., `from app.config import settings`)

## Database

- SQLAlchemy 2.0+ async API — `AsyncSession`, `async_sessionmaker`, `create_async_engine`
- All models use `Mapped[]` type annotations with `mapped_column()` — never the legacy `Column()` API
- All models inherit from `Base` in `app.db.session` — engine and `async_session` also live there
- Naming conventions on `Base.metadata` — never manually name constraints (Alembic needs predictable names)
- Use `select()` for queries — never the legacy `session.query()` API
- One session per request via `get_db()` dependency — `expire_on_commit=False` on all sessionmakers
- Alembic for migrations — always autogenerate with `mise run db:generate "message"`, always review the generated file before applying
- Order: create/update the SQLAlchemy model first, then generate the Alembic migration, then load data — you can't generate a migration without a model

## Layered Architecture

When building CRUD for a new entity, create files in this order:

1. `schemas/<entity>.py` — Pydantic models with `ConfigDict(from_attributes=True)`. Nest related schemas (e.g., `HotelResponse` inside `DealResponse`).
2. `repositories/<entity>.py` — async functions using `select()`. Pure data access — no HTTP concepts, no exceptions.
3. `services/<entity>.py` — thin orchestration. Services raise `HTTPException` (404, 409) — repositories never do.
4. `routers/<entity>.py` — uses the `DB` alias, `response_model` on each endpoint. Status codes explicit: 200 reads, 201 creates.
5. Wire the router in `main.py` via `app.include_router()`.
6. One integration test per endpoint in `tests/`.

## Testing

- `asyncio_mode = "strict"` — every async test must have `@pytest.mark.asyncio`
- In-memory SQLite via `aiosqlite` — no Docker needed to run tests
- httpx `AsyncClient` with `ASGITransport` — not FastAPI's sync `TestClient`
- `app.dependency_overrides[get_db]` to inject the test database session
- `--cov=src --cov-report=term-missing` — coverage is always reported

## Logging

- structlog for all logging — use `get_logger(__name__)`, not stdlib `logging.getLogger()`
- Log events as key-value pairs: `logger.info("event_name", key=value)` — not format strings
- Request ID is automatically included via middleware and contextvars — don't pass it manually

## Configuration

- pydantic-settings `BaseSettings` for all configuration — env vars are the source of truth
- Defaults point to local Docker Compose services (e.g., `postgresql+asyncpg://super@localhost:5432/super`)
- `.env` file for local overrides, environment variables in production
