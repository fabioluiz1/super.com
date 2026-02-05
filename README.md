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

**`Base(DeclarativeBase)`** — base class for ORM models. Every model inherits from `Base`. SQLAlchemy uses this to track all models and their table metadata, which `Base.metadata.create_all()` uses to create tables.

##### pydantic-settings

`Settings(BaseSettings)` automatically reads environment variables. Field `database_url` maps to env var `DATABASE_URL` (case-insensitive). In production, set `DATABASE_URL` in the environment; in development, the default points to Docker Compose PostgreSQL. This 12-factor pattern keeps secrets out of code.

### Docker

PostgreSQL 16 runs via Docker Compose with trust authentication (passwordless localhost).

```bash
docker compose up -d db       # start PostgreSQL
docker compose down            # stop all services
docker compose down -v         # stop and delete data volume
```
