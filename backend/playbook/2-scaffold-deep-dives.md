# Scaffold Deep-Dives — "If Asked, Expand"

Expanded answers for follow-up questions about the tech stack during the 30-second pitch
(Phase 1). Each section matches one line from the pitch.

---

## mise as the single interface

mise manages the Python version, all tasks, and the git pre-commit hook. Every command is
`mise run <task>` — there's nothing to memorize.

In a monorepo, mise also manages tool versions for other workspaces from a single `.mise.toml` at
the root. For example, a monorepo with a React frontend, a FastAPI backend, and a Python ML service
(each in its own workspace — `frontend/`, `backend/`, `ml/`) would pin Node, Python 3.12, and
Python 3.11 + CUDA respectively. Tasks like `test:frontend`, `test:backend`, `test:ml` provide a
uniform interface — contributors run `mise run <task>` regardless of whether the underlying tool
is npm, pytest, or a custom training script.

mise also pins infrastructure tools — Terraform, kubectl, AWS CLI, Helm — so the entire team
runs the same versions. Tasks like `mise run infra:plan`, `mise run infra:apply` wrap
`terraform plan/apply` with the right workspace and var files, preventing the "works on my machine"
problem where one developer has Terraform 1.5 and another has 1.8.

## Pre-commit + tests as guardrails

A pre-commit hook runs ruff, mypy strict, and pytest on every commit. AI-generated code that has
type errors or breaks tests gets rejected automatically. The guardrails let me move fast with AI
without sacrificing quality.

## FastAPI + async

async/await throughout — every endpoint, dependency, and database call is non-blocking. When a
request hits `await db.execute()`, it yields control to the event loop, which serves other requests
during the wait. One process handles hundreds of concurrent DB-bound requests with a connection
pool — no extra workers, no wasted memory.

```python
async def get_deals(db: DB) -> list[Deal]:
    result = await db.execute(select(Deal))
    return result.scalars().all()
```

For a visual comparison of sync (Flask/Gunicorn) vs async (FastAPI/uvicorn) concurrency models, see
[2.1-fastapi-async-vs-sync.md](2.1-fastapi-async-vs-sync.md).

## PostgreSQL for dev and tests

Docker Compose runs Postgres for both development (`super`) and tests (`super_test`). The test
database is created automatically by `docker/init-test-db.sql` on first container startup.

Each test fixture creates all tables (`Base.metadata.create_all`), runs the test, then drops
everything (`Base.metadata.drop_all`). Postgres supports transactional DDL, so this is clean
and reliable — no leftover rows from a previous test causing flaky failures.

Using the same database engine for dev and tests eliminates dialect mismatches — check
constraints, date functions, `ILIKE`, and every other Postgres-specific feature works
identically in both environments.

## SQLAlchemy 2.0

Python's ORM with an explicit query builder separate from model definitions. You write ORM queries
(never raw SQL) but control the full query shape — joins, subqueries, window functions, CTEs.
Supports 1:N and M:N relationships via `relationship()` with `back_populates`. Version 2.0 adds
`Mapped[]` type annotations so mypy checks every model field and query result at compile time.

```python
select(Deal).where(Deal.city == "Toronto")   # query builder
```

For a comparison with ActiveRecord (Rails) and Prisma (Node), see
[2.2-sqlalchemy-vs-activerecord-vs-prisma.md](2.2-sqlalchemy-vs-activerecord-vs-prisma.md).

## Alembic

SQLAlchemy's migration tool — a hybrid between desired-state (Prisma) and operations-based
(Rails). You write the desired state as SQLAlchemy models, then Alembic autogenerates a Python
migration file with explicit operations (`create_table`, `add_column`, etc.). You review and edit
the operations before applying.

```
SQLAlchemy models
  → alembic revision --autogenerate
  → Python migration file
  → you review/edit
  → alembic upgrade head
  → applied to DB
```

This gives you autogeneration from models (less manual work) plus editable operations (full control
for data migrations, complex changes, or splitting steps). Migrations form a linked list of
diffs — each file has a `revision` ID and a `down_revision` pointer to the previous one.

For a detailed comparison with Prisma and Rails, see
[2.3-alembic-vs-prisma-vs-rails.md](2.3-alembic-vs-prisma-vs-rails.md).
