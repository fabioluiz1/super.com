from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hotel
from app.schemas.hotel import HotelCreate, HotelUpdate


async def list_hotels(
    db: AsyncSession, skip: int, limit: int, name: str | None = None
) -> list[Hotel]:
    """Return a page of hotels ordered by id."""
    stmt = select(Hotel).order_by(Hotel.id).offset(skip).limit(limit)
    if name:
        stmt = stmt.where(Hotel.name.ilike(f"%{name}%"))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_all_hotels(
    db: AsyncSession,
    skip: int,
    limit: int,
    name: str | None = None,
    max_per_group: int | None = None,
) -> list[Hotel]:
    """Return hotels ordered by city then id.

    When *max_per_group* is set, at most that many hotels are returned per
    city using a ``ROW_NUMBER()`` window function so the filtering happens
    entirely in the database.
    """
    if max_per_group is not None:
        row_num = (
            func.row_number()
            .over(
                partition_by=Hotel.city,
                order_by=Hotel.id,
            )
            .label("row_num")
        )

        inner = select(Hotel.id, row_num)
        if name:
            inner = inner.where(Hotel.name.ilike(f"%{name}%"))
        subq = inner.subquery()

        stmt = (
            select(Hotel)
            .join(subq, Hotel.id == subq.c.id)
            .where(subq.c.row_num <= max_per_group)
            .order_by(Hotel.city, Hotel.id)
            .offset(skip)
            .limit(limit)
        )
    else:
        stmt = select(Hotel).order_by(Hotel.city, Hotel.id).offset(skip).limit(limit)
        if name:
            stmt = stmt.where(Hotel.name.ilike(f"%{name}%"))

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_hotels(db: AsyncSession, name: str | None = None) -> int:
    """Return total number of hotels."""
    stmt = select(func.count(Hotel.id))
    if name:
        stmt = stmt.where(Hotel.name.ilike(f"%{name}%"))
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_hotel_by_id(db: AsyncSession, hotel_id: int) -> Hotel | None:
    """Return a single hotel by primary key, or None if it doesn't exist."""
    stmt = select(Hotel).where(Hotel.id == hotel_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_hotel(db: AsyncSession, data: HotelCreate) -> Hotel:
    """Insert a new hotel and return it with DB-generated fields."""
    hotel = Hotel(**data.model_dump())
    db.add(hotel)
    await db.flush()
    await db.refresh(hotel)
    return hotel


async def update_hotel(db: AsyncSession, hotel: Hotel, data: HotelUpdate) -> Hotel:
    """Apply partial update to an existing hotel."""
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(hotel, field, value)
    await db.flush()
    await db.refresh(hotel)
    return hotel


async def delete_hotel(db: AsyncSession, hotel: Hotel) -> None:
    """Hard-delete a hotel."""
    await db.delete(hotel)
    await db.flush()
