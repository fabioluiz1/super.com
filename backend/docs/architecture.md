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
from app.services import book as book_svc

router = APIRouter()


@router.get("/books", response_model=BookListResponse, status_code=200)
async def list_books(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> BookListResponse:
    """List paginated books with nested author data."""
    result = await book_svc.get_books(db, skip, limit)
    return BookListResponse.model_validate(result)


@router.get("/books/{book_id}", response_model=BookResponse, status_code=200)
async def get_book_by_id(db: DB, book_id: int) -> BookResponse:
    """Get a single book by ID. Returns 404 if not found."""
    book = await book_svc.get_book(db, book_id)
    return BookResponse.model_validate(book)
```

Wire it in `main.py`:

```python
from app.routers.book import router as book_router

app.include_router(book_router)
```

## REST Operations

Every entity exposes a standard set of HTTP endpoints. The verb determines the operation, the status code confirms the outcome.

| Verb | Route | Status | Purpose |
|------|-------|--------|---------|
| `GET` | `/books` | 200 | List (paginated) |
| `GET` | `/books/{id}` | 200 | Detail |
| `POST` | `/books` | 201 | Create |
| `PATCH` | `/books/{id}` | 200 | Partial update |
| `DELETE` | `/books/{id}` | 204 | Hard delete |

### Why PATCH, not PUT

PUT means full replacement — the client must send every field, even the ones that didn't change. If a field is missing from the request, the server is supposed to set it to its default or null. That's fragile: a client that forgets to include `original_price` accidentally wipes it.

PATCH is partial — the client sends only what changed. The schema uses `Optional` fields with `None` as the default, and the repository skips any field that wasn't provided. Since PATCH already covers the PUT use case — a client *can* send all fields in a PATCH — most APIs ship PATCH and skip PUT entirely. There's no reason to maintain a separate full-replacement endpoint.

### Why hard DELETE

This demo uses hard delete (`DELETE FROM`) — the row is permanently removed. It's simpler: no `WHERE is_deleted = false` on every query, no stale rows accumulating in the table, no ambiguity about what "deleted" means.

In production, soft delete (`is_deleted` flag + `deleted_at` timestamp) preserves audit history and allows undo. But it complicates every query — you must filter deleted rows everywhere, including joins and aggregations. Use soft delete when regulatory or business requirements demand it; default to hard delete otherwise.

### Create schema

A separate request schema defines which fields the client provides. The database generates `id`, `created_at`, and `updated_at`.

```python
# schemas/book.py
class BookCreate(BaseModel):
    title: str
    pages: int = Field(gt=0)
    author_id: int
```

### Update schema

All fields are `Optional` — the client sends only what changed. Validators still apply to provided fields.

```python
# schemas/book.py
class BookUpdate(BaseModel):
    title: str | None = None
    pages: int | None = Field(default=None, gt=0)
```

### Create / Update / Delete in the repository

```python
# repositories/book.py
async def create_book(db: AsyncSession, data: BookCreate) -> Book:
    # model_dump() converts the Pydantic schema to a dict
    # ** unpacks it as keyword arguments
    book = Book(**data.model_dump())
    db.add(book)
    await db.flush()
    # reload the book from DB with its author relationship populated,
    # so the returned object has nested author data for serialization
    await db.refresh(book, ["author"])
    return book


async def update_book(db: AsyncSession, book: Book, data: BookUpdate) -> Book:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(book, field, value)
    await db.flush()
    await db.refresh(book, ["author"])
    return book


async def delete_book(db: AsyncSession, book: Book) -> None:
    await db.delete(book)
    await db.flush()
```

### Create / Update / Delete in the service

The service validates preconditions (entity exists, FK is valid) and raises domain exceptions — the router never touches the repository directly.

```python
# services/book.py
from app.exceptions import NotFoundError
from app.repositories import author as author_repo
from app.repositories import book as book_repo
from app.schemas.book import BookCreate, BookUpdate


async def create_book(db: AsyncSession, data: BookCreate) -> Book:
    """Validate the author FK exists, then create the book."""
    author = await author_repo.get_author_by_id(db, data.author_id)
    if author is None:
        raise NotFoundError("Author", data.author_id)
    return await book_repo.create_book(db, data)


async def update_book(db: AsyncSession, book_id: int, data: BookUpdate) -> Book:
    """Fetch the book or raise 404, then apply partial update."""
    book = await book_repo.get_book_by_id(db, book_id)
    if book is None:
        raise NotFoundError("Book", book_id)
    return await book_repo.update_book(db, book, data)


async def delete_book(db: AsyncSession, book_id: int) -> None:
    """Fetch the book or raise 404, then delete."""
    book = await book_repo.get_book_by_id(db, book_id)
    if book is None:
        raise NotFoundError("Book", book_id)
    await book_repo.delete_book(db, book)
```

### Write endpoints in the router

```python
# routers/book.py
from app.services import book as book_svc


@router.post("/books", response_model=BookResponse, status_code=201)
async def create_book(db: DB, data: BookCreate) -> BookResponse:
    book = await book_svc.create_book(db, data)
    return BookResponse.model_validate(book)


@router.patch("/books/{book_id}", response_model=BookResponse, status_code=200)
async def update_book(db: DB, book_id: int, data: BookUpdate) -> BookResponse:
    book = await book_svc.update_book(db, book_id, data)
    return BookResponse.model_validate(book)


@router.delete("/books/{book_id}", status_code=204)
async def delete_book(db: DB, book_id: int) -> None:
    await book_svc.delete_book(db, book_id)
```

### 5. Integration Tests (`tests/test_<entity>.py`)

See [testing.md](testing.md) for reference test examples covering happy path, nested relations, 404, pagination, and validation (422).

## Error Handling

See [error-handling.md](error-handling.md) for the error envelope format, domain exceptions, and error schemas.

## Shared Dependencies (`app.dependencies`)

- `DB = Annotated[AsyncSession, Depends(get_db)]` — the database session type alias used by all endpoints
- Defined in `dependencies.py` (not `main.py`) to avoid circular imports when routers are registered in main

## New Entity Checklist

1. [ ] `schemas/<entity>.py` — response models with `from_attributes`, `EntityListResponse = PaginatedResponse[EntityResponse]`, `EntityCreate`, `EntityUpdate` (all-optional)
2. [ ] `repositories/<entity>.py` — `list_`, `count_`, `get_by_id`, `create_`, `update_`, `delete_`
3. [ ] `services/<entity>.py` — return `Paginated[Model]`, orchestration functions, domain exceptions
4. [ ] `routers/<entity>.py` — GET (200), POST (201), PATCH (200), DELETE (204) with `response_model`, `Query` params, `DB` dependency
5. [ ] `main.py` — `app.include_router(<entity>_router)`
6. [ ] `tests/test_<entity>.py` — happy path, 404, pagination, validation (422), create, update, delete
