# Super.com Mock Interview

This monorepo uses [mise](https://mise.jdx.dev/) as a single tool to replace three:

- **`mise install`** pins and installs the exact Node and Python versions from `.mise.toml` — replaces **nvm** / **pyenv**
- **`mise run <task>`** runs linters and formatters defined in `.mise.toml` — replaces **per-project npm scripts at the root**
- **`mise run setup`** generates a git pre-commit hook that runs all checks before every commit — replaces:
  - **husky** — installs git hooks (e.g., pre-commit) so scripts run automatically on `git commit`
  - **lint-staged** — filters `git diff --staged` to only lint/format files you're about to commit, not the entire codebase

## Quickstart

```bash
mise trust
mise install
mise run install:frontend
mise run install:backend
mise run setup          # install git pre-commit hook
```

### Frontend

#### Stylelint

Lints Sass files with `postcss-sass` for indented syntax support.

```bash
mise run lint:sass     # check for style errors
```

#### Code Quality

**ESLint** handles correctness — it finds bugs and enforces code rules (unused variables, implicit `any`, unsafe patterns). **Prettier** handles formatting — whitespace, line breaks, quotes, semicolons. `eslint-config-prettier` disables ESLint's formatting rules so only Prettier handles style.

##### ESLint

- `typescript-eslint` strict preset
- `no-explicit-any` enforced as error
- `max-len` warns at 100 characters (URLs and strings excluded)

```bash
mise run lint          # check for lint errors
```

##### Prettier

- `printWidth` 100 characters
- `singleQuote` enabled
- `semi` disabled (no semicolons)
- `trailingComma` all

```bash
mise run format        # auto-format all source files
mise run format:check  # check formatting without writing
```

### Backend

#### Ruff

Handles both linting and formatting for Python — a single Rust-based tool that replaces flake8 (linting), isort (import sorting), black (formatting), and pylint (code analysis). One config in `pyproject.toml`, one CLI. See `[tool.ruff]` in `backend/pyproject.toml` for settings and enabled rules.

```bash
mise run lint:backend         # check for lint errors
mise run format:backend       # auto-format Python files
mise run format:backend:check # check formatting without writing
```

#### mypy

Static type checker — analyzes type annotations without running the code. Catches type mismatches, missing return types, and incorrect function signatures at commit time instead of at runtime. `strict = true` enforces type annotations everywhere. The `pydantic.mypy` plugin lets mypy understand Pydantic model field types and validators.

See [docs/mypy.md](docs/mypy.md) for a detailed explanation of why `strict = true` is a best practice, with BAD/GOOD examples for each check it enables.

Alternatives: pyright (Microsoft, faster but less ecosystem integration), pytype (Google, inference-heavy).

```bash
mise run typecheck:backend    # run static type analysis
```

#### pytest

Test framework with fixture-based dependency injection. `asyncio_mode = "strict"` requires explicit `@pytest.mark.asyncio` on async tests — this is the recommended mode because it prevents accidental async tests (e.g., forgetting to `await` a coroutine) from silently passing.

Key plugins:
- `pytest-asyncio` — run async test functions and fixtures
- `pytest-cov` — measure code coverage
- `httpx` — async HTTP client used as FastAPI test client (replaces `requests` for async)
- `aiosqlite` — in-memory SQLite for fast isolated tests without Docker

Alternatives: unittest (stdlib, class-based, more verbose), nose2 (legacy).

```bash
mise run test:backend         # run tests with coverage report
```

##### Test Fixtures ([conftest.py](backend/tests/conftest.py))

**SQLite in-memory database** — [`sqlite+aiosqlite:///:memory:`](backend/tests/conftest.py#L11) creates a fresh database for each test run. No Docker needed, tests run fast, complete isolation. The `aiosqlite` driver provides async support for SQLite.

**[`db` fixture](backend/tests/conftest.py#L17-L27)** — creates tables before yielding a session, drops tables after. Each test gets a clean database state. The `async with engine.begin()` provides a transaction for DDL operations.

**[`client` fixture](backend/tests/conftest.py#L30-L45)** — httpx `AsyncClient` configured to call the FastAPI app directly via `ASGITransport` (no network, just in-process calls). `app.dependency_overrides[get_db]` replaces the real database dependency with the test database session — this is FastAPI's dependency injection override pattern.

**Why httpx over TestClient?** — FastAPI's `TestClient` uses `requests` which is sync-only. For async endpoints with async database calls, you need an async test client. httpx provides `AsyncClient` that works with `ASGITransport` to call ASGI apps directly.

#### FastAPI

High-performance async web framework built on:
- **Starlette** — ASGI framework (routing, middleware)
- **Pydantic** — data validation and serialization

**ASGI** (Asynchronous Server Gateway Interface) is the async successor to WSGI (Web Server Gateway Interface). WSGI (2003) is sync-only — one request = one thread. ASGI (2016) is async-native — supports `async/await`, WebSockets, and long-lived connections, allowing thousands of concurrent requests without thousands of threads.

**uvicorn** is the ASGI server that runs FastAPI apps. It receives HTTP requests and calls your FastAPI app as an async coroutine.

Alternatives: Flask (sync WSGI, simpler), Django (batteries-included, ORM built-in), Litestar (similar to FastAPI, different design choices).

##### Application Structure ([main.py](backend/src/app/main.py))

**[`app = FastAPI(lifespan=lifespan)`](backend/src/app/main.py#L18)** — creates the application instance. The `lifespan` parameter accepts an async context manager that runs setup code before the first request and cleanup code on shutdown.

**[`@asynccontextmanager async def lifespan(app)`](backend/src/app/main.py#L7-L15)** — the lifespan context manager. Code before `yield` runs on startup (warm up caches, connect to services), code after `yield` runs on shutdown (close connections). This replaces the deprecated `@app.on_event("startup")` pattern.

##### Running the Server

**uvicorn** is the ASGI server that runs FastAPI apps. `--reload` watches for file changes and restarts (dev only). `--app-dir src` adds `src/` to Python's path so `from app.main import app` works.

```bash
mise run dev:backend          # start server with hot reload on :8000
```

- `http://localhost:8000/health` — health check endpoint (pings database)
- `http://localhost:8000/docs` — Swagger UI (auto-generated from type hints)
- `http://localhost:8000/redoc` — ReDoc (alternative API docs)

#### Database

##### Connection URL

`postgresql+asyncpg://super@localhost:5432/super`

- `postgresql` — SQLAlchemy dialect name for PostgreSQL
- `asyncpg` — the async driver (DBAPI). SQLAlchemy needs a driver to actually talk to the database. `asyncpg` is a high-performance async PostgreSQL driver written in Cython. Alternatives: `psycopg` (sync, most popular), `psycopg[async]` (async version of psycopg3)
- `super@localhost:5432/super` — `user@host:port/database`. No password because Docker Compose uses trust authentication

##### SQLAlchemy Async Setup

**`create_async_engine(url)`** — creates a connection pool to the database. The engine doesn't connect immediately; it creates connections on demand and reuses them. Pool settings like `pool_size`, `max_overflow`, `pool_timeout` control how many concurrent connections are allowed.

**`async_sessionmaker(engine, expire_on_commit=False)`** — factory that creates `AsyncSession` instances. A session is a unit-of-work: it tracks objects you've loaded/modified, and flushes changes to the database when you commit. `expire_on_commit=False` keeps objects usable after commit without re-querying — important for async because accessing expired attributes would need a sync database call.

**`get_db()`** — FastAPI dependency that yields a session per request. The `async with` context manager ensures the session is closed even if the request raises an exception. This pattern (one session per request, injected via `Depends(get_db)`) is standard for FastAPI + SQLAlchemy.

**`Base(DeclarativeBase)`** — base class for ORM models. Every model inherits from `Base`. SQLAlchemy uses this to track all models and their table metadata. The `naming_convention` on `Base.metadata` ensures all constraints (primary keys, foreign keys, indexes) have predictable names — this is required for Alembic to generate correct `DROP CONSTRAINT` statements.

##### pydantic-settings

`Settings(BaseSettings)` automatically reads environment variables. Field `database_url` maps to env var `DATABASE_URL` (case-insensitive). In production, set `DATABASE_URL` in the environment; in development, the default points to Docker Compose PostgreSQL. This 12-factor pattern keeps secrets out of code.

See [docs/database.md](docs/database.md) for connection pool tuning and naming convention details.

##### Alembic Migrations

Database migrations track schema changes in version-controlled Python files. Like Rails migrations, each migration has `upgrade()` and `downgrade()` functions. Alembic autogenerates migrations by comparing your models to the current database schema.

**Workflow:**
1. Modify models in `backend/src/app/models/`
2. Generate migration: `mise run db:generate "add users table"`
3. Review generated file in `backend/alembic/versions/`
4. Apply migration: `mise run db:migrate`

**Configuration** ([alembic/env.py](backend/alembic/env.py)):
- Imports `Base.metadata` to detect model changes
- Gets `DATABASE_URL` from `app.config.settings`
- Uses async engine (same as the app)

```bash
mise run db:migrate              # run pending migrations (alembic upgrade head)
mise run db:rollback             # rollback last migration (alembic downgrade -1)
mise run db:generate "message"   # generate migration from model changes
```

### Docker

#### Services

- **db** — PostgreSQL 16 with trust authentication (passwordless localhost)
- **backend** — FastAPI app built from `backend/Dockerfile`

#### Dockerfile (Multi-Stage Build)

**Build stage** (`ghcr.io/astral-sh/uv:python3.12-bookworm-slim`) — uses uv's official image which includes Python 3.12 and uv pre-installed. Installs dependencies first (cached unless lock file changes), then copies source and installs the project. `--frozen` ensures the lock file is used exactly. `--no-dev` excludes dev dependencies.

**Runtime stage** (`python:3.12-slim-bookworm`) — minimal image without uv or build tools. Only the `.venv` and source code are copied from the build stage. This keeps the final image small (~150MB vs ~500MB with build tools).

**Why multi-stage?** — separates build-time dependencies (compilers, uv) from runtime. Smaller image = faster deploys, smaller attack surface.

#### Health Checks

The `db` service has a health check (`pg_isready`) so the `backend` service waits for PostgreSQL to be ready before starting. `depends_on: condition: service_healthy` ensures proper startup order.

#### Commands

```bash
docker compose up -d db       # start PostgreSQL only (for local dev)
docker compose up -d          # start all services
docker compose up --build     # rebuild images and start
docker compose down            # stop all services
docker compose down -v         # stop and delete data volume
docker compose logs -f backend # tail backend logs
```
