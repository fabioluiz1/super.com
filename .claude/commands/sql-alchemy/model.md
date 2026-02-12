# SQLAlchemy Model Generator

You generate SQLAlchemy 2.0+ model classes from natural language descriptions.

## Target file

`backend/src/app/models.py` — read it first, then append new classes. Never overwrite existing models.

## Conventions

- Import `Base` from `app.db.session` (already re-exported at top of models.py)
- Use `Mapped[T]` with `mapped_column()` — never legacy `Column()`
- `relationship()` with `back_populates=` on both sides
- `ForeignKey` columns always get `index=True`
- `String` columns require an explicit max length: `mapped_column(String(N))`
- `date` for date-only columns, `DateTime(timezone=True)` for timestamps
- `CheckConstraint` must have `name=` kwarg (pattern: descriptive snake_case, e.g. `rating_range`, `price_gte_zero`)
- Multi-column uniqueness via `UniqueConstraint` in `__table_args__`
- Line length max 100 characters
- Add only the imports that are actually needed for the new models (don't duplicate existing imports)

## Reference example

```python
from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base  # noqa: F401


class Author(Base):
    __tablename__ = "authors"
    __table_args__ = (UniqueConstraint("first_name", "last_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(200), unique=True)

    books: Mapped[list["Book"]] = relationship(back_populates="author")


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),
        CheckConstraint("price >= 0", name="price_gte_zero"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("authors.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    price: Mapped[float]
    rating: Mapped[int]
    published_on: Mapped[date]
    is_available: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    author: Mapped["Author"] = relationship(back_populates="books")
```

## After writing

Run these commands to auto-fix formatting:

```bash
cd backend && uv run ruff format src/app/models.py && uv run ruff check --fix src/app/models.py
```

## Task

$ARGUMENTS
