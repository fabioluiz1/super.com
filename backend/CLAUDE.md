# Backend — Claude Code Instructions

## Layered Architecture

See [docs/architecture.md](docs/architecture.md) for layers, error handling, and shared dependencies.

Four layers: Routers → Services → Repositories → Schemas. When adding a new entity, create files in this order: `schemas/<entity>.py` → `repositories/<entity>.py` → `services/<entity>.py` → `routers/<entity>.py`, then wire the router in `main.py`.

## FastAPI Patterns

- All endpoints, dependencies, and database calls use `async/await`
- Dependency injection via `Annotated[Type, Depends(fn)]` — always declare dependencies as type annotations, never call `get_db()` or similar functions directly in endpoint bodies
- DB session type: `from app.dependencies import DB`, then use `db: DB` as a parameter in endpoints
- Lifespan context manager for startup/shutdown — not the deprecated `@app.on_event()`
- Error responses use `{"error": {"code": "...", "message": "..."}}` envelope — see [docs/architecture.md](docs/architecture.md)
- Source layout: `backend/src/app/` — imports start with `app.` (e.g., `from app.config import settings`)

## Database

- SQLAlchemy 2.0+ async API — `AsyncSession`, `async_sessionmaker`, `create_async_engine`
- All models use `Mapped[]` type annotations with `mapped_column()` — never the legacy `Column()` API
- All models inherit from `Base` in `app.db.session` — engine and `async_session` also live there
- Never manually name constraints — use the naming conventions on `Base.metadata` so Alembic autogenerate produces consistent, predictable names
- Use `select()` for queries — never the legacy `session.query()` API
- One session per request via `get_db()` dependency — `expire_on_commit=False` on all sessionmakers
- Alembic for migrations — autogenerate with `mise run db:generate "message"`, then review the generated file for correctness (e.g., dropped columns, wrong defaults) before applying with `mise run db:migrate`
- Order: create/update the SQLAlchemy model first, then generate the Alembic migration, then load data — Alembic can't detect changes without a model to diff against

## API Conventions

- All list endpoints return paginated responses with `total`, `skip`, `limit`, and `items` fields
- All query parameters use snake_case
- Always use `selectinload()` in queries that need related objects — async SQLAlchemy blocks lazy loading at runtime (`MissingGreenlet`)

## Testing

- `asyncio_mode = "strict"` — every async test must have `@pytest.mark.asyncio`
- Separate Postgres database (`super_test`) — same engine as dev, no dialect mismatches
- httpx `AsyncClient` with `ASGITransport` — not FastAPI's sync `TestClient`
- `app.dependency_overrides[get_db]` to inject the test database session
- Run tests with `uv run pytest -x --tb=short` — coverage is reported via `--cov=src --cov-report=term-missing`

## Code Style

- Ruff handles both linting and formatting — line-length 100, target `py312`
- mypy `strict = true` — every function must have complete type annotations (parameters + return)
- `pydantic.mypy` plugin enabled — Pydantic models are preferred over raw dicts for structured data

## Logging

- structlog for all logging — use `get_logger(__name__)`, not stdlib `logging.getLogger()`
- Log events as key-value pairs: `logger.info("event_name", key=value)` — not format strings
- Request ID is automatically bound via middleware and contextvars — don't pass it manually

## Configuration

- pydantic-settings `BaseSettings` for all configuration — env vars are the source of truth
- Defaults point to local Docker Compose services (e.g., `postgresql+asyncpg://super@localhost:5432/super`)
- `.env` file for local overrides, environment variables in production

## Python & Dependencies

- Python 3.12, pinned in `.mise.toml`
- uv for package management — `uv sync` to install, `uv run` to execute tools
- Production deps in `[project.dependencies]`, dev deps in `[dependency-groups.dev]` inside `backend/pyproject.toml`
