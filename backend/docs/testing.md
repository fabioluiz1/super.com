# Testing

## When to Use Each Test Type

### Integration tests (primary)

Test through HTTP via `AsyncClient`, hitting the real test database. This is the default for CRUD endpoints because the layers are thin — mocking the repo just duplicates the implementation.

Write integration tests for:
- Every endpoint (happy path + error cases)
- Response shape (correct fields, nested relations, pagination envelope)
- Query parameter validation (422 on invalid input)
- Business logic outcomes (computed fields, filtered results)

### Unit tests

Test a single function in isolation, mocking its dependencies. Only worth the overhead when there's real logic to verify — not for pass-through code.

Write unit tests for:
- Service functions with conditional logic, calculations, or data transformations
- Utility functions (parsers, formatters, validators)
- Edge cases that are hard to trigger through HTTP (e.g., race conditions, specific error paths)

Don't unit test:
- Repositories — they're thin wrappers around SQLAlchemy; integration tests cover them
- Routers — they just call services and serialize; integration tests cover them
- Services that only forward to a single repo call

### End-to-end tests

Test the full deployed system including external services, auth, network. These live outside the backend repo (e.g., in a separate test suite or CI pipeline) and are not covered here.

## Test Infrastructure

### Fixtures (`conftest.py`)

Two fixtures power every test:

- **`db`** — creates all tables before the test, yields an `AsyncSession`, drops all tables after. Each test gets a clean database.
- **`client`** — an httpx `AsyncClient` that sends requests to the FastAPI app in-process (no real HTTP server). Uses `dependency_overrides` to inject the test `db` session instead of the production one.

```python
# Usage — just declare them as parameters, pytest injects automatically
async def test_something(client: AsyncClient) -> None:
    resp = await client.get("/endpoint")
```

The test database is a separate Postgres instance (`super_test`) — same engine as dev, no dialect mismatches.

### Factories (`factories.py`)

Factory functions create model instances with sensible defaults. Every field has a default except those that must be unique or are required foreign keys.

```python
from tests.factories import make_author, make_book

author = make_author()                           # all defaults
author = make_author(name="Custom Name")         # override one field
book = make_book(isbn="978-0-13-4", author_id=1) # required params have no default
```

When adding a new entity, add a `make_<entity>()` function to `factories.py`.

### Seeds (`seeds.py`)

The `seeded_db` fixture populates the database with realistic test data — enough rows to test pagination, relationships, and aggregations. It depends on the `db` fixture, so tables are already created.

```python
# Usage — request seeded_db instead of db when you need pre-populated data
async def test_with_data(client: AsyncClient, seeded_db: None) -> None:
    resp = await client.get("/books")
    assert resp.json()["total"] > 0

# Tests that need an empty database just use client (which depends on db)
async def test_empty(client: AsyncClient) -> None:
    resp = await client.get("/books")
    assert resp.json()["total"] == 0
```

Seeds are registered via `pytest_plugins = ["tests.seeds"]` in conftest — pytest won't discover fixtures from arbitrary modules without this.

## Async Test Rules

- `asyncio_mode = "strict"` — every async test **must** have `@pytest.mark.asyncio`
- Use httpx `AsyncClient` with `ASGITransport` — not FastAPI's sync `TestClient`
- Run with: `uv run pytest -x --tb=short`

## Reference Examples

All examples use a fictional **Author / Book** domain. Replace model names and endpoints when adding a real entity.

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_books_returns_paginated_response(client: AsyncClient, seeded_db: None) -> None:
    resp = await client.get("/books")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body
    assert "total" in body
    assert "skip" in body
    assert "limit" in body
    assert isinstance(body["items"], list)


@pytest.mark.asyncio
async def test_list_books_includes_nested_author(client: AsyncClient, seeded_db: None) -> None:
    resp = await client.get("/books")
    item = resp.json()["items"][0]
    assert "author" in item
    assert "id" in item["author"]
    assert "name" in item["author"]


@pytest.mark.asyncio
async def test_get_book_returns_single_book(client: AsyncClient, seeded_db: None) -> None:
    # Get a valid ID from the list endpoint first
    list_resp = await client.get("/books")
    book_id = list_resp.json()["items"][0]["id"]

    resp = await client.get(f"/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == book_id
    assert "author" in resp.json()


@pytest.mark.asyncio
async def test_get_book_not_found_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/books/999999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_list_books_invalid_skip_returns_422(client: AsyncClient) -> None:
    resp = await client.get("/books", params={"skip": -1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_books_invalid_limit_returns_422(client: AsyncClient) -> None:
    resp = await client.get("/books", params={"limit": 0})
    assert resp.status_code == 422
```
