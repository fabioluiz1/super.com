# Layered Architecture

Every endpoint follows four layers. Each layer has one job and only calls the layer directly below it. Dependency injection (`Depends()`) wires them together — it resolves sessions, services, and config before handler code runs.

All examples use a fictional **Author / Book** domain (one-to-many). Replace model names and fields when adding a real entity.

## Pagination (`schemas/pagination.py`)

Two generic types already exist in the scaffold — parameterize them per entity, don't redefine pagination fields:

- **`PaginatedResponse[T]`** (Pydantic) — use in **schemas** and **routers** for HTTP responses
- **`Paginated[T]`** (dataclass) — use in **services** for internal results

```python
# schemas/book.py
BookListResponse = PaginatedResponse[BookResponse]

# services/book.py
async def get_books(db, skip, limit) -> Paginated[Book]: ...

# routers/book.py — convert dataclass → Pydantic
result = await get_books(db, skip, limit)
return BookListResponse.model_validate(result)
```

## Layers

Listed bottom-up — this is the order you create files when adding a new entity.

### 1. Schemas (`schemas/<entity>.py`)

- Define the shape of request and response data as Pydantic models
- Set `model_config = {"from_attributes": True}` so schemas can serialize SQLAlchemy models directly
- Nest related schemas when the API returns joined data (e.g., a parent summary inside a child response)
- Use `PaginatedResponse[EntityResponse]` for list endpoints — don't redefine pagination fields

```python
from datetime import datetime

from pydantic import BaseModel

from app.schemas.pagination import PaginatedResponse


class AuthorInBook(BaseModel):
    """Author summary nested inside a book response."""

    model_config = {"from_attributes": True}

    id: int
    name: str
    created_at: datetime
    updated_at: datetime


class BookResponse(BaseModel):
    """Single book with its nested author."""

    model_config = {"from_attributes": True}

    id: int
    title: str
    pages: int
    author_id: int
    created_at: datetime
    updated_at: datetime
    author: AuthorInBook


BookListResponse = PaginatedResponse[BookResponse]
```

### 2. Repositories (`repositories/<entity>.py`)

- Execute database queries — pure data access with no knowledge of HTTP or business rules
- Every function takes `AsyncSession` as its first argument and returns model instances (or `None`)
- Never raise exceptions; return `None` or an empty list and let the service decide

```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Book


async def list_books(db: AsyncSession, skip: int, limit: int) -> list[Book]:
    """Return a page of books with their authors eagerly loaded."""
    stmt = (
        select(Book)
        .options(selectinload(Book.author))
        .order_by(Book.id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_books(db: AsyncSession) -> int:
    """Return total number of books."""
    result = await db.execute(select(func.count(Book.id)))
    return result.scalar_one()


async def get_book_by_id(db: AsyncSession, book_id: int) -> Book | None:
    """Return a single book by primary key, or None if it doesn't exist."""
    stmt = select(Book).options(selectinload(Book.author)).where(Book.id == book_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
```

### 3. Services (`services/<entity>.py`)

- Contain business logic and orchestrate calls to one or more repositories
- Raise domain exceptions (e.g., `NotFoundError`, `ConflictError`) — never `HTTPException`
- Keep services thin; if a service just forwards to a repo, that's fine
- Use the shared `Paginated[T]` dataclass for list results — don't redefine pagination fields per entity

```python
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models import Book
from app.repositories.book import count_books, get_book_by_id, list_books
from app.schemas.pagination import Paginated


async def get_books(db: AsyncSession, skip: int, limit: int) -> Paginated[Book]:
    """Fetch a paginated list of books."""
    items = await list_books(db, skip, limit)
    total = await count_books(db)
    return Paginated(items=items, total=total, skip=skip, limit=limit)


async def get_book(db: AsyncSession, book_id: int) -> Book:
    """Fetch a single book or raise NotFoundError."""
    book = await get_book_by_id(db, book_id)
    if book is None:
        raise NotFoundError("Book", book_id)
    return book
```

### 4. Routers (`routers/<entity>.py`)

- Receive HTTP requests and return HTTP responses — the only layer that knows about HTTP verbs, status codes, and query parameters
- Declare `response_model` on every endpoint so FastAPI validates the output
- Use explicit status codes: `200` for reads, `201` for creates
- Wire each router in `main.py` via `app.include_router()`

```python
from fastapi import APIRouter, Query

from app.dependencies import DB
from app.schemas.book import BookListResponse, BookResponse
from app.services.book import get_book, get_books

router = APIRouter()


@router.get("/books", response_model=BookListResponse, status_code=200)
async def list_books(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> BookListResponse:
    """List paginated books with nested author data."""
    result = await get_books(db, skip, limit)
    return BookListResponse.model_validate(result)


@router.get("/books/{book_id}", response_model=BookResponse, status_code=200)
async def get_book_by_id(db: DB, book_id: int) -> BookResponse:
    """Get a single book by ID. Returns 404 if not found."""
    book = await get_book(db, book_id)
    return BookResponse.model_validate(book)
```

Wire it in `main.py`:

```python
from app.routers.book import router as book_router

app.include_router(book_router)
```

### 5. Integration Tests (`tests/test_<entity>.py`)

See [testing.md](testing.md) for reference test examples covering happy path, nested relations, 404, pagination, and validation (422).

## Error Handling

See [error-handling.md](error-handling.md) for the error envelope format, domain exceptions, and error schemas.

## Shared Dependencies (`app.dependencies`)

- `DB = Annotated[AsyncSession, Depends(get_db)]` — the database session type alias used by all endpoints
- Defined in `dependencies.py` (not `main.py`) to avoid circular imports when routers are registered in main

## New Entity Checklist

1. [ ] `schemas/<entity>.py` — response models with `from_attributes`, `EntityListResponse = PaginatedResponse[EntityResponse]`
2. [ ] `repositories/<entity>.py` — `list_`, `count_`, `get_by_id` (add more as needed)
3. [ ] `services/<entity>.py` — return `Paginated[Model]`, orchestration functions, domain exceptions
4. [ ] `routers/<entity>.py` — endpoints with `response_model`, `Query` params, `DB` dependency
5. [ ] `main.py` — `app.include_router(<entity>_router)`
6. [ ] `tests/test_<entity>.py` — happy path, 404, pagination, validation (422)
