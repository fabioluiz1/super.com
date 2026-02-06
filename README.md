# Super.com Mock Interview

This monorepo uses [mise](https://mise.jdx.dev/) as a single tool to replace three:

- **`mise install`** pins and installs the exact Node and Python versions from `.mise.toml` — replaces **nvm** / **pyenv**
- **`mise run <task>`** runs linters and formatters defined in `.mise.toml` — replaces **per-project npm scripts at the root**
- **`mise run setup`** installs git hooks — replaces **husky** + **lint-staged** + **commitlint**:
  - **pre-commit** — runs all linters, formatters, and typecheck before every commit
  - **commit-msg** — validates commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, etc.)

## Quickstart

```bash
mise trust
mise install
mise run install:frontend
mise run install:backend
mise run setup          # install git hooks (pre-commit + commit-msg)
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

Dependencies are managed by [uv](https://docs.astral.sh/uv/) — a Rust-based Python package manager that replaces pip, poetry, and pipenv. `mise run install:backend` runs `uv sync`, which installs exact versions from `uv.lock`.

#### Architecture

```
backend/
├── pyproject.toml          # dependencies + tool config (ruff, mypy, pytest)
├── Dockerfile              # multi-stage build (see docs/docker.md)
├── alembic.ini             # migration config
├── .env.example            # environment variable template
├── alembic/
│   ├── env.py              # async migration runner
│   └── versions/           # generated migration files
├── src/app/
│   ├── main.py             # FastAPI app, lifespan, routes
│   ├── config.py           # pydantic-settings (env vars -> typed config)
│   ├── logging.py          # structlog JSON logging setup
│   ├── middleware.py        # request ID tracing
│   └── db/session.py       # async engine, session factory, Base model
└── tests/
    ├── conftest.py          # fixtures (in-memory SQLite, async HTTP client)
    └── test_health.py       # health endpoint test
```

#### Code Quality

##### Ruff

Handles both linting and formatting for Python — a single Rust-based tool that replaces flake8 (linting), isort (import sorting), black (formatting), and pylint (code analysis). One config in `pyproject.toml`, one CLI. See `[tool.ruff]` in `backend/pyproject.toml` for settings and enabled rules.

```bash
mise run lint:backend         # check for lint errors
mise run format:backend       # auto-format Python files
mise run format:backend:check # check formatting without writing
```

##### mypy

Static type checker — analyzes type annotations without running the code. Catches type mismatches, missing return types, and incorrect function signatures at commit time instead of at runtime. `strict = true` enforces type annotations everywhere. The `pydantic.mypy` plugin lets mypy understand Pydantic model field types and validators.

See [docs/mypy.md](docs/mypy.md) for a detailed explanation of why `strict = true` is a best practice, with BAD/GOOD examples for each check it enables.

Alternatives: pyright (Microsoft, faster but less ecosystem integration), pytype (Google, inference-heavy).

```bash
mise run typecheck:backend    # run static type analysis
```

#### Testing

pytest with async support, in-memory SQLite for isolation, and httpx for async HTTP calls. `asyncio_mode = "strict"` requires explicit `@pytest.mark.asyncio` on async tests — prevents accidental async tests from silently passing.

See [docs/testing.md](docs/testing.md) for fixture details, the dependency override pattern, and why httpx is used over FastAPI's TestClient.

```bash
mise run test:backend         # run tests with coverage report
```

#### FastAPI

High-performance async web framework built on Starlette (ASGI routing/middleware) and Pydantic (data validation). Runs on uvicorn, an ASGI server.

See [docs/fastapi.md](docs/fastapi.md) for ASGI vs WSGI, the lifespan pattern, dependency injection, and application structure.

```bash
mise run dev:backend          # start server with hot reload on :8000
```

- `http://localhost:8000/health` — health check (pings database)
- `http://localhost:8000/docs` — Swagger UI (auto-generated from type hints)
- `http://localhost:8000/redoc` — ReDoc (alternative API docs)

#### Structured Logging

JSON-structured logs via [structlog](https://www.structlog.org/). Every log event is a JSON object with automatic context binding — fields like `request_id`, `timestamp`, and `level` are included without passing them explicitly.

Request ID middleware assigns a unique `X-Request-ID` to every request and binds it to all logs via Python's `contextvars`. All logs during a single request share the same `request_id`, making it trivial to trace a request across log lines.

See [docs/structlog.md](docs/structlog.md) for the processor pipeline, contextvars pattern, and end-to-end tracing example.

#### Database

PostgreSQL with async SQLAlchemy. The connection URL format is `postgresql+asyncpg://user@host:port/database` — `asyncpg` is a high-performance async PostgreSQL driver written in Cython.

Configuration is loaded from environment variables via pydantic-settings — field `database_url` maps to env var `DATABASE_URL`. In development, defaults point to Docker Compose PostgreSQL. See `.env.example` for all settings.

See [docs/database.md](docs/database.md) for SQLAlchemy async setup, connection pooling, and naming conventions.

#### Alembic Migrations

Database migrations track schema changes in version-controlled Python files. Each migration has `upgrade()` and `downgrade()` functions. Alembic autogenerates migrations by comparing your models to the current database schema.

**Workflow:**
1. Modify models in `backend/src/app/models/`
2. Generate migration: `mise run db:generate "add users table"`
3. Review generated file in `backend/alembic/versions/`
4. Apply migration: `mise run db:migrate`

```bash
mise run db:migrate              # run pending migrations (alembic upgrade head)
mise run db:rollback             # rollback last migration (alembic downgrade -1)
mise run db:generate "message"   # generate migration from model changes
```

### Docker

PostgreSQL 16 and FastAPI backend via Docker Compose. Multi-stage Dockerfile keeps the final image small (~150MB) by separating build tools from runtime.

See [docs/docker.md](docs/docker.md) for multi-stage build details and service configuration.

```bash
docker compose up -d db       # start PostgreSQL only (for local dev)
docker compose up -d          # start all services
docker compose up --build     # rebuild images and start
docker compose down            # stop all services
docker compose down -v         # stop and delete data volume
docker compose logs -f backend # tail backend logs
```
