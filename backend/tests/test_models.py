from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Deal, Hotel
from tests.factories import make_deal, make_hotel


# ---------------------------------------------------------------------------
# 1. Persistence — 2 hotels and 7 deals
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_seed_creates_2_hotels_and_7_deals(seeded_db: AsyncSession) -> None:
    hotels = (await seeded_db.execute(select(Hotel))).scalars().all()
    deals = (await seeded_db.execute(select(Deal))).scalars().all()

    assert len(hotels) == 2
    assert len(deals) == 7


# ---------------------------------------------------------------------------
# 2. Associations — hotel loads its own deals
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_hotel_loads_its_own_deals(seeded_db: AsyncSession) -> None:
    stmt = select(Hotel).options(selectinload(Hotel.deals)).order_by(Hotel.name)
    hotels = (await seeded_db.execute(stmt)).scalars().all()

    lakeside, metro = hotels[0], hotels[1]
    assert lakeside.name == "Lakeside Court"
    assert len(lakeside.deals) == 4
    assert metro.name == "Metro Tower"
    assert len(metro.deals) == 3

    for deal in lakeside.deals:
        assert deal.hotel_id == lakeside.id


# ---------------------------------------------------------------------------
# 3. Check constraints — violation tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field, value",
    [
        ("rating", 0),
        ("rating", 6),
        ("price_per_night", Decimal("0")),
        ("price_per_night", Decimal("-1")),
        ("price_per_night", Decimal("100000")),
        ("original_price", Decimal("0")),
        ("original_price", Decimal("100000")),
        ("discount_percent", -1),
        ("discount_percent", 101),
    ],
    ids=[
        "rating_below_min",
        "rating_above_max",
        "price_per_night_zero",
        "price_per_night_negative",
        "price_per_night_above_max",
        "original_price_zero",
        "original_price_above_max",
        "discount_below_min",
        "discount_above_max",
    ],
)
async def test_check_constraint_violation(db: AsyncSession, field: str, value: object) -> None:
    hotel = make_hotel()
    db.add(hotel)
    await db.flush()

    async with db.begin_nested():
        deal = make_deal(external_id=9999, hotel_id=hotel.id)
        setattr(deal, field, value)
        db.add(deal)

        with pytest.raises((IntegrityError, DBAPIError)):
            await db.flush()


# ---------------------------------------------------------------------------
# 4. Cannot delete hotel if deals are associated (RESTRICT)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cannot_delete_hotel_with_deals(seeded_db: AsyncSession) -> None:
    hotel = (await seeded_db.execute(select(Hotel).limit(1))).scalar_one()

    async with seeded_db.begin_nested():
        await seeded_db.delete(hotel)
        with pytest.raises(IntegrityError):
            await seeded_db.flush()


# ---------------------------------------------------------------------------
# 5. Can delete deal then the respective hotel
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_delete_deals_then_hotel(seeded_db: AsyncSession) -> None:
    stmt = select(Hotel).options(selectinload(Hotel.deals)).limit(1)
    hotel = (await seeded_db.execute(stmt)).scalar_one()

    for deal in hotel.deals:
        await seeded_db.delete(deal)
    await seeded_db.flush()

    await seeded_db.delete(hotel)
    await seeded_db.flush()

    remaining = (
        await seeded_db.execute(select(Hotel).where(Hotel.id == hotel.id))
    ).scalar_one_or_none()
    assert remaining is None


# ---------------------------------------------------------------------------
# 6. Unique phone constraint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_duplicate_phone_raises(db: AsyncSession) -> None:
    db.add(make_hotel(name="Hotel A", phone="+1-111-111-1111"))
    await db.flush()

    async with db.begin_nested():
        db.add(make_hotel(name="Hotel B", city="Toronto", phone="+1-111-111-1111"))
        with pytest.raises(IntegrityError):
            await db.flush()


# ---------------------------------------------------------------------------
# 7. Unique (name, city, country) constraint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_duplicate_hotel_location_raises(db: AsyncSession) -> None:
    db.add(make_hotel(name="Grand", city="Paris", country="France", phone="+33-1"))
    await db.flush()

    async with db.begin_nested():
        db.add(make_hotel(name="Grand", city="Paris", country="France", phone="+33-2"))
        with pytest.raises(IntegrityError):
            await db.flush()


# ---------------------------------------------------------------------------
# 8. created_at / updated_at auto-populated
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_timestamps_auto_populated(db: AsyncSession) -> None:
    hotel = make_hotel()
    db.add(hotel)
    await db.flush()

    deal = make_deal(external_id=9998, hotel_id=hotel.id)
    db.add(deal)
    await db.commit()

    await db.refresh(hotel)
    await db.refresh(deal)

    assert hotel.created_at is not None
    assert hotel.updated_at is not None
    assert deal.created_at is not None
    assert deal.updated_at is not None


# ---------------------------------------------------------------------------
# 9. checkin_date <= checkout_date constraint
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_checkin_after_checkout_raises(db: AsyncSession) -> None:
    hotel = make_hotel()
    db.add(hotel)
    await db.flush()

    async with db.begin_nested():
        deal = make_deal(
            external_id=9997,
            hotel_id=hotel.id,
            checkin_date=date(2025, 12, 10),
            checkout_date=date(2025, 12, 1),
        )
        db.add(deal)

        with pytest.raises(IntegrityError):
            await db.flush()
