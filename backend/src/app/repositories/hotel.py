from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hotel
from app.schemas.hotel import HotelCreate, HotelUpdate


async def list_hotels(db: AsyncSession, skip: int, limit: int) -> list[Hotel]:
    """Return a page of hotels ordered by id."""
    stmt = select(Hotel).order_by(Hotel.id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_hotels(db: AsyncSession) -> int:
    """Return total number of hotels."""
    result = await db.execute(select(func.count(Hotel.id)))
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
