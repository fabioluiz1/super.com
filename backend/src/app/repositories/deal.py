"""Deal data-access layer.

Pure query functions — no business logic, no HTTP concerns.
Each function takes a session and returns models or scalars.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Deal


async def list_deals(db: AsyncSession, skip: int, limit: int) -> list[Deal]:
    """Return a page of deals with their hotels eagerly loaded."""
    stmt = (
        select(Deal).options(selectinload(Deal.hotel)).order_by(Deal.id).offset(skip).limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_deals(db: AsyncSession) -> int:
    """Return total number of deals."""
    stmt = select(func.count(Deal.id))
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_avg_ratings_by_hotel(db: AsyncSession, hotel_ids: list[int]) -> dict[int, float]:
    """Return average deal rating per hotel for the given hotel IDs."""
    if not hotel_ids:
        return {}
    stmt = (
        select(Deal.hotel_id, func.avg(Deal.rating))
        .where(Deal.hotel_id.in_(hotel_ids))
        .group_by(Deal.hotel_id)
    )
    result = await db.execute(stmt)
    return {row[0]: float(row[1]) for row in result.all()}
