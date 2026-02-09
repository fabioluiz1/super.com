"""SQLAlchemy models.

Define all ORM models here. They must inherit from Base so that
Alembic's autogenerate can detect them.

Example:

    class Deal(Base):
        __tablename__ = "deals"
        id: Mapped[int] = mapped_column(primary_key=True)
        ...
"""

from app.db.session import Base  # noqa: F401 — re-exported for convenience
