# Claude Code Instructions

## Documentation Standards

All documentation must be **didactic, specific, and developer-friendly** — written as if explaining to a junior developer.

- Explain what each tool does and why it exists before listing configuration
- When two tools overlap (e.g., ESLint vs Prettier), explain the boundary between them
- One bullet per rule/setting — no prose lists like "no any types allowed, max line length 100"
- Keep descriptions concise but never vague — "replaces husky" is vague, "installs git hooks so scripts run automatically on `git commit`" is specific
- DX (Developer Experience) must be excellent: quickstart should get a dev running in copy-paste commands

## README Structure

- Root README covers monorepo-wide setup and all tool documentation
- Subproject READMEs (frontend/, backend/) contain only interview instructions and project-specific setup
- Don't duplicate information across READMEs — pick one location (DRY)
- Quickstart block: only setup commands, no lint/format commands (those go in tool sections)
- Tool sections show `mise run` commands (the monorepo interface), not `npm run` (the subproject interface)
- Build documentation incrementally — each commit adds only the docs for what that commit introduces

## Git Workflow

- Use `git rebase --autosquash` with `git commit --fixup=<sha>` to edit previous commits
- Never use `git reset --soft` — it changes the log story
- Each commit should be atomic: one logical change with its corresponding documentation, mise tasks, and README updates

## Mise

- mise is the single tool for version pinning, task running, and git hooks — replacing nvm, husky, and lint-staged
- All linter/formatter/build commands are defined as mise tasks in `.mise.toml`
- Task names must be specific and unambiguous: `install:frontend` not `install`, `lint:sass` not `lint:css`
- The `pre-commit` task depends on all check tasks and runs them in parallel
- `mise run setup` installs the git pre-commit hook — this is part of the quickstart, not optional

## Monorepo Structure

```
.mise.toml          # tool versions + all tasks
README.md           # quickstart + tool docs (succinct)
docs/               # deep-dive guides (linked from README)
frontend/           # React + Vite + TypeScript
backend/            # FastAPI + SQLAlchemy + PostgreSQL
```

## Frontend Code Quality

- Stylelint for Sass (indented syntax via postcss-sass)
- ESLint with typescript-eslint strict preset (no `any`, max-len 100)
- Prettier for formatting (100 chars, single quotes, no semicolons)
- eslint-config-prettier disables ESLint rules that conflict with Prettier
- All checks run on every commit via the pre-commit hook

## Backend

### Python & Dependencies

- Python 3.12, pinned in `.mise.toml`
- uv for package management — `uv sync` to install, `uv run` to execute tools
- Production deps in `[project.dependencies]`, dev deps in `[dependency-groups.dev]` inside `backend/pyproject.toml`

### Code Style

- Ruff handles both linting and formatting — line-length 100, target `py312`
- mypy `strict = true` — every function must have complete type annotations (parameters + return)
- `pydantic.mypy` plugin enabled — Pydantic models are preferred over raw dicts for structured data

### FastAPI Patterns

- Async everywhere — all endpoints, dependencies, and database calls use `async/await`
- Dependency injection via `Annotated[Type, Depends(fn)]` — never call dependencies manually
- Lifespan context manager for startup/shutdown — not the deprecated `@app.on_event()`
- Global exception handler logs with request context and returns generic errors — no stack traces to clients
- Source layout: `backend/src/app/` — imports start with `app.` (e.g., `from app.config import settings`)

### Database

- SQLAlchemy 2.0+ async API — `AsyncSession`, `async_sessionmaker`, `create_async_engine`
- All models inherit from `Base` in `app.db.session`
- Naming conventions on `Base.metadata` — never manually name constraints (Alembic needs predictable names)
- One session per request via `get_db()` dependency — `expire_on_commit=False` on all sessionmakers
- Alembic for migrations — always autogenerate with `mise run db:generate "message"`, always review the generated file before applying

### Testing

- `asyncio_mode = "strict"` — every async test must have `@pytest.mark.asyncio`
- In-memory SQLite via `aiosqlite` — no Docker needed to run tests
- httpx `AsyncClient` with `ASGITransport` — not FastAPI's sync `TestClient`
- `app.dependency_overrides[get_db]` to inject the test database session
- `--cov=src --cov-report=term-missing` — coverage is always reported

### Logging

- structlog for all logging — use `get_logger(__name__)`, not stdlib `logging.getLogger()`
- Log events as key-value pairs: `logger.info("event_name", key=value)` — not format strings
- Request ID is automatically included via middleware and contextvars — don't pass it manually

### Configuration

- pydantic-settings `BaseSettings` for all configuration — env vars are the source of truth
- Defaults point to local Docker Compose services (e.g., `postgresql+asyncpg://super@localhost:5432/super`)
- `.env` file for local overrides, environment variables in production
