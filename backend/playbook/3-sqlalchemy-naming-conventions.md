# SQLAlchemy ORM Naming Conventions

Optional talking point — use if the interviewer asks about the `Base` class or constraint naming.

## What to show

Open `db/session.py` and show the base class:

```python
naming_convention: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=naming_convention)
```

## What to say

> "Without these naming conventions, Alembic generates random constraint names like `sa0_pk`. That
> breaks future migrations because Alembic can't match constraints by name when it needs to drop or
> rename them. With the convention, every constraint gets a predictable name — `pk_deals`,
> `fk_deals_hotel_id_hotels` — so autogenerate works reliably across the whole migration chain."
