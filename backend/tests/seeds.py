"""Reusable seed data fixtures for integration tests."""

from decimal import Decimal

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import make_deal, make_hotel


@pytest_asyncio.fixture
async def seeded_db(db: AsyncSession) -> AsyncSession:
    """Seed 2 hotels and 7 deals for integration tests."""
    hotel_a = make_hotel(
        name="Lakeside Court", city="Berlin", country="Germany", phone="+49-30-555-3780"
    )
    hotel_b = make_hotel(
        name="Metro Tower", city="Chicago", country="United States", phone="+1-312-555-5133"
    )
    db.add_all([hotel_a, hotel_b])
    await db.flush()

    deals = [
        make_deal(
            external_id=1001,
            hotel_id=hotel_a.id,
            rating=5,
            room_type="suite",
            price_per_night=Decimal("176.18"),
        ),
        make_deal(
            external_id=1002,
            hotel_id=hotel_a.id,
            rating=4,
            room_type="deluxe",
            price_per_night=Decimal("193.35"),
        ),
        make_deal(
            external_id=1003,
            hotel_id=hotel_a.id,
            rating=3,
            room_type="economy",
            price_per_night=Decimal("50.70"),
        ),
        make_deal(
            external_id=1004,
            hotel_id=hotel_a.id,
            rating=5,
            room_type="penthouse",
            price_per_night=Decimal("401.94"),
        ),
        make_deal(
            external_id=1005,
            hotel_id=hotel_b.id,
            rating=4,
            room_type="standard",
            price_per_night=Decimal("37.11"),
        ),
        make_deal(
            external_id=1006,
            hotel_id=hotel_b.id,
            rating=3,
            room_type="deluxe",
            price_per_night=Decimal("107.70"),
        ),
        make_deal(
            external_id=1007,
            hotel_id=hotel_b.id,
            rating=5,
            room_type="suite",
            price_per_night=Decimal("135.50"),
        ),
    ]
    db.add_all(deals)
    await db.commit()
    return db
