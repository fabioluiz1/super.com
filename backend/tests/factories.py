"""Factory functions for creating model instances in tests."""

from datetime import date
from decimal import Decimal

from app.models import Deal, Hotel


def make_hotel(
    *,
    name: str = "Lakeside Court",
    city: str = "Berlin",
    country: str = "Germany",
    phone: str = "+49-30-555-3780",
) -> Hotel:
    return Hotel(name=name, city=city, country=country, phone=phone)


def make_deal(
    *,
    external_id: int,
    hotel_id: int,
    rating: int = 4,
    room_type: str = "suite",
    price_per_night: Decimal = Decimal("176.18"),
    original_price: Decimal = Decimal("244.69"),
    discount_percent: int = 28,
    checkin_date: date = date(2025, 11, 22),
    checkout_date: date = date(2025, 12, 6),
    is_available: bool = True,
    categories: str = "luxury,boutique",
) -> Deal:
    return Deal(
        external_id=external_id,
        hotel_id=hotel_id,
        rating=rating,
        room_type=room_type,
        price_per_night=price_per_night,
        original_price=original_price,
        discount_percent=discount_percent,
        checkin_date=checkin_date,
        checkout_date=checkout_date,
        is_available=is_available,
        categories=categories,
    )
