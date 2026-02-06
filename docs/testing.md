# Testing

pytest with fixture-based dependency injection and async support.

## Configuration ([pyproject.toml](../backend/pyproject.toml))

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
asyncio_mode = "strict"
addopts = "--cov=src --cov-report=term-missing --no-header -q"
```

- `asyncio_mode = "strict"` — requires explicit `@pytest.mark.asyncio` on async tests. Prevents accidental async tests (forgetting to `await`) from silently passing.
- `--cov=src --cov-report=term-missing` — show coverage with uncovered line numbers.

## Key Plugins

| Plugin | Purpose |
|--------|---------|
| `pytest-asyncio` | Run async test functions and fixtures |
| `pytest-cov` | Measure code coverage |
| `httpx` | Async HTTP client used as FastAPI test client |
| `aiosqlite` | In-memory SQLite for fast isolated tests without Docker |

Alternatives to pytest: unittest (stdlib, class-based, more verbose), nose2 (legacy).

## Test Fixtures ([conftest.py](../backend/tests/conftest.py))

### In-Memory Database

```python
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine = create_async_engine(TEST_DATABASE_URL)
```

Uses SQLite in memory instead of PostgreSQL:

- No Docker needed to run tests
- Each test gets a fresh, isolated database
- Fast — no network, no disk I/O

### `db` Fixture

```python
@pytest_asyncio.fixture
async def db() -> AsyncIterator[AsyncSession]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)   # Create tables
    async with async_session() as session:
        yield session                                     # Test runs here
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)      # Drop tables
```

Each test gets a clean database: tables created before, dropped after. `engine.begin()` provides a transaction for DDL operations (CREATE TABLE, DROP TABLE).

### `client` Fixture

```python
@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()
```

**`app.dependency_overrides`** — FastAPI's dependency injection override. Replaces the real `get_db` (which connects to PostgreSQL) with a function that yields the test's SQLite session.

**`ASGITransport(app=app)`** — calls the FastAPI app directly, in-process. No network, no server. httpx sends a request, Starlette routes it, your endpoint runs, and the response comes back — all in the same Python process.

### Why httpx over TestClient?

FastAPI's `TestClient` uses `requests` (sync-only). For async endpoints with async database calls, you need an async test client. httpx provides `AsyncClient` with `ASGITransport` for direct ASGI app calls.

## Writing a Test

```python
@pytest.mark.asyncio                                    # Required with asyncio_mode = "strict"
async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- `@pytest.mark.asyncio` — marks this as an async test. Without it, pytest would try to call the coroutine synchronously and the test would silently pass without running.
- `client` — the `AsyncClient` fixture from conftest.py. pytest injects it automatically.
