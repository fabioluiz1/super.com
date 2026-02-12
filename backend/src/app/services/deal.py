"""Deal business logic.

Orchestrates repository calls and attaches computed fields
(avg_rating) before the data reaches the serialization layer.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Deal
from app.repositories.deal import count_deals, get_avg_ratings_by_hotel, list_deals


@dataclass
class PaginatedDeals:
    """Container for a page of deals plus pagination metadata."""

    items: list[Deal]
    total: int
    skip: int
    limit: int


async def get_deals(db: AsyncSession, skip: int, limit: int) -> PaginatedDeals:
    """Fetch a paginated list of deals with avg_rating attached to each hotel.

    Three fixed queries per call (no N+1):
    1. Paginated deals with eager-loaded hotels
    2. Total deal count
    3. Average rating grouped by hotel
    """
    deals, total = await list_deals(db, skip, limit), await count_deals(db)

    hotel_ids = list({deal.hotel_id for deal in deals})
    avg_ratings = await get_avg_ratings_by_hotel(db, hotel_ids)

    for deal in deals:
        deal.hotel.avg_rating = avg_ratings.get(deal.hotel_id, 0.0)  # type: ignore[attr-defined]

    return PaginatedDeals(items=deals, total=total, skip=skip, limit=limit)
