from fastapi import APIRouter, Query

from app.dependencies import DB
from app.schemas.hotel import (
    HotelCreate,
    HotelGroupedResponse,
    HotelListResponse,
    HotelResponse,
    HotelUpdate,
)
from app.services import hotel as hotel_svc

router = APIRouter(prefix="/api/v1")


@router.get("/hotels", response_model=HotelListResponse, status_code=200)
async def list_hotels(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    name: str = Query(None, min_length=1),
) -> HotelListResponse:
    """List paginated hotels."""
    result = await hotel_svc.get_hotels(db, skip, limit, name)
    return HotelListResponse.model_validate(result)


@router.get("/hotels/grouped", response_model=HotelGroupedResponse, status_code=200)
async def list_hotels_grouped(
    db: DB,
    by: str = Query("city", pattern="^city$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    name: str = Query(None, min_length=1),
    max_per_group: int = Query(2, ge=1, le=100),
) -> HotelGroupedResponse:
    """List hotels grouped by city."""
    return HotelGroupedResponse.model_validate(
        await hotel_svc.get_hotels_grouped_by_city(
            db, skip, limit, name, max_per_group=max_per_group
        )
    )


@router.get("/hotels/{hotel_id}", response_model=HotelResponse, status_code=200)
async def get_hotel(db: DB, hotel_id: int) -> HotelResponse:
    """Get a single hotel by ID. Returns 404 if not found."""
    hotel = await hotel_svc.get_hotel(db, hotel_id)
    return HotelResponse.model_validate(hotel)


@router.post("/hotels", response_model=HotelResponse, status_code=201)
async def create_hotel(db: DB, data: HotelCreate) -> HotelResponse:
    """Create a new hotel."""
    hotel = await hotel_svc.create_hotel(db, data)
    return HotelResponse.model_validate(hotel)


@router.patch("/hotels/{hotel_id}", response_model=HotelResponse, status_code=200)
async def update_hotel(db: DB, hotel_id: int, data: HotelUpdate) -> HotelResponse:
    """Partial update a hotel. Returns 404 if not found."""
    hotel = await hotel_svc.update_hotel(db, hotel_id, data)
    return HotelResponse.model_validate(hotel)


@router.delete("/hotels/{hotel_id}", status_code=204)
async def delete_hotel(db: DB, hotel_id: int) -> None:
    """Delete a hotel. Returns 404 if not found."""
    await hotel_svc.delete_hotel(db, hotel_id)
