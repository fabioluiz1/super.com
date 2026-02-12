from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotFoundError
from app.models import Hotel
from app.repositories import hotel as hotel_repo
from app.schemas.hotel import HotelCreate, HotelUpdate
from app.schemas.pagination import Paginated


async def get_hotels(
    db: AsyncSession, skip: int, limit: int, name: str | None = None
) -> Paginated[Hotel]:
    """Fetch a paginated list of hotels."""
    items = await hotel_repo.list_hotels(db, skip, limit, name)
    total = await hotel_repo.count_hotels(db, name)
    return Paginated(items=items, total=total, skip=skip, limit=limit)


async def get_hotel(db: AsyncSession, hotel_id: int) -> Hotel:
    """Fetch a single hotel or raise NotFoundError."""
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    if hotel is None:
        raise NotFoundError("Hotel", hotel_id)
    return hotel


async def create_hotel(db: AsyncSession, data: HotelCreate) -> Hotel:
    """Create a new hotel."""
    return await hotel_repo.create_hotel(db, data)


async def update_hotel(db: AsyncSession, hotel_id: int, data: HotelUpdate) -> Hotel:
    """Fetch the hotel or raise 404, then apply partial update."""
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    if hotel is None:
        raise NotFoundError("Hotel", hotel_id)
    return await hotel_repo.update_hotel(db, hotel, data)


async def delete_hotel(db: AsyncSession, hotel_id: int) -> None:
    """Fetch the hotel or raise 404, then delete."""
    hotel = await hotel_repo.get_hotel_by_id(db, hotel_id)
    if hotel is None:
        raise NotFoundError("Hotel", hotel_id)
    await hotel_repo.delete_hotel(db, hotel)
