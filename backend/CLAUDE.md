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

Every endpoint follows four layers. Each layer has one job and only calls the layer directly below it. Dependency injection (`Depends()`) wires them together — it resolves sessions, services, and config before handler code runs.

1. **Routers** (`routers/<entity>.py`)
   - Receive HTTP requests and return HTTP responses — the only layer that knows about HTTP verbs, status codes, and query parameters
   - Translate domain exceptions from services into `HTTPException` — e.g., `EntityNotFound` → `404`, `ConflictError` → `409`
   - Declare `response_model` on every endpoint so FastAPI validates the output
   - Use explicit status codes: `200` for reads, `201` for creates
   - Wire each router in `main.py` via `app.include_router()`

2. **Services** (`services/<entity>.py`)
   - Contain business logic and orchestrate calls to one or more repositories
   - Raise domain exceptions (e.g., `EntityNotFound`, `ConflictError`) — never `HTTPException`
   - Keep services thin; if a service just forwards to a repo, that's fine

3. **Repositories** (`repositories/<entity>.py`)
   - Execute database queries — pure data access with no knowledge of HTTP or business rules
   - Every function takes `AsyncSession` as its first argument and returns model instances (or `None`)
   - Never raise exceptions; return `None` or an empty list and let the service decide

4. **Schemas** (`schemas/<entity>.py`)
   - Define the shape of request and response data as Pydantic models
   - Set `ConfigDict(from_attributes=True)` so schemas can serialize SQLAlchemy models directly
   - Nest related schemas when the API returns joined data (e.g., `HotelSchema` inside `DealResponse`)

When building CRUD for a new entity, create files bottom-up (schemas → repos → services → routers), then wire the router and add one integration test per endpoint.

## API Conventions

- All list endpoints return paginated responses with `total`, `skip`, `limit` fields
- All query parameters use snake_case
- Always use `selectinload()` for relationships — never rely on lazy loading (causes N+1)
- Deal responses always include nested hotel data via eager loading

## Testing

- `asyncio_mode = "strict"` — every async test must have `@pytest.mark.asyncio`
- Separate Postgres database (`super_test`) — same engine as dev, no dialect mismatches
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
