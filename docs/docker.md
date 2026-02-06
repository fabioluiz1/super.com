# Docker

## Services ([docker-compose.yaml](../docker-compose.yaml))

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `db` | `postgres:16-alpine` | 5432 | PostgreSQL with trust auth (passwordless) |
| `backend` | Built from `backend/Dockerfile` | 8000 | FastAPI application |

The `backend` service waits for PostgreSQL to be healthy before starting (`depends_on: condition: service_healthy`). The `db` service runs `pg_isready` every 5 seconds as its health check.

## Multi-Stage Dockerfile ([Dockerfile](../backend/Dockerfile))

The Dockerfile has two stages: **build** (install dependencies) and **runtime** (run the app).

### Build Stage

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project    # 1. Install deps (cached layer)

COPY src/ src/
RUN uv sync --frozen --no-dev                          # 2. Install project
```

- `ghcr.io/astral-sh/uv` — uv's official image with Python 3.12 and uv pre-installed
- `--frozen` — use the lock file exactly (no dependency resolution)
- `--no-dev` — skip dev dependencies (ruff, pytest, mypy)
- Dependencies are installed before copying source code — Docker caches this layer, so `docker build` only re-installs deps when `pyproject.toml` or `uv.lock` change

### Runtime Stage

```dockerfile
FROM python:3.12-slim-bookworm

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "src"]
```

Only the `.venv` and source code are copied from the builder. No uv, no build tools, no dev dependencies.

**Result:** ~150MB final image vs ~500MB with all build tools. Smaller image = faster deploys, smaller attack surface.

## Commands

```bash
docker compose up -d db       # start PostgreSQL only (for local dev)
docker compose up -d          # start all services
docker compose up --build     # rebuild images and start
docker compose down            # stop all services
docker compose down -v         # stop and delete data volume
docker compose logs -f backend # tail backend logs
```
