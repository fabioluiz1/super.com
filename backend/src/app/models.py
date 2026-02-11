"""SQLAlchemy models.

Define all ORM models here. They must inherit from Base so that
Alembic's autogenerate can detect them.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base  # noqa: F401 — re-exported for convenience


class Hotel(Base):
    __tablename__ = "hotels"
    __table_args__ = (UniqueConstraint("name", "city", "country", name="uq_hotel_location"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(30), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    deals: Mapped[list["Deal"]] = relationship(back_populates="hotel")


class Deal(Base):
    __tablename__ = "deals"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="rating_range"),
        CheckConstraint(
            "price_per_night > 0 AND price_per_night <= 99999",
            name="price_per_night_range",
        ),
        CheckConstraint(
            "original_price > 0 AND original_price <= 99999",
            name="original_price_range",
        ),
        CheckConstraint(
            "discount_percent >= 0 AND discount_percent <= 100",
            name="discount_percent_range",
        ),
        CheckConstraint(
            "checkin_date <= checkout_date",
            name="checkin_before_checkout",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[int] = mapped_column(unique=True)
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id"), index=True)
    rating: Mapped[int]
    room_type: Mapped[str] = mapped_column(String(50))
    price_per_night: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    original_price: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    discount_percent: Mapped[int]
    checkin_date: Mapped[date]
    checkout_date: Mapped[date]
    is_available: Mapped[bool]
    categories: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    hotel: Mapped["Hotel"] = relationship(back_populates="deals")
