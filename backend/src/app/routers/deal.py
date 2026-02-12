"""Deal endpoints."""

from fastapi import APIRouter, Query

from app.dependencies import DB
from app.schemas.deal import DealListResponse
from app.services.deal import get_deals

router = APIRouter()


@router.get("/deals", response_model=DealListResponse, status_code=200)
async def list_deals(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
) -> DealListResponse:
    """List paginated deals with nested hotel data and computed avg_rating."""
    result = await get_deals(db, skip, limit)
    return DealListResponse(
        items=result.items,
        total=result.total,
        skip=result.skip,
        limit=result.limit,
    )
