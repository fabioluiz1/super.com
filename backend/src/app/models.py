"""SQLAlchemy models.

Define all ORM models here. They must inherit from Base so that
Alembic's autogenerate can detect them.

Example:

    class Deal(Base):
        __tablename__ = "deals"
        id: Mapped[int] = mapped_column(primary_key=True)
        ...
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base  # noqa: F401 — re-exported for convenience


class Hotel(Base):
    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100))
