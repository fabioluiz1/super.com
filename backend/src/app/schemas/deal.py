"""Deal response schemas.

Pydantic models for the GET /deals endpoint. HotelInDeal carries a computed
avg_rating that the service layer attaches before serialization.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class HotelInDeal(BaseModel):
    """Hotel summary nested inside a deal response."""

    model_config = {"from_attributes": True}

    id: int
    name: str
    city: str
    country: str
    phone: str
    avg_rating: float
    created_at: datetime
    updated_at: datetime


class DealResponse(BaseModel):
    """Single deal with its nested hotel."""

    model_config = {"from_attributes": True}

    id: int
    external_id: int
    hotel_id: int
    rating: int
    room_type: str
    price_per_night: Decimal
    original_price: Decimal
    discount_percent: int
    checkin_date: date
    checkout_date: date
    is_available: bool
    categories: str
    created_at: datetime
    updated_at: datetime
    hotel: HotelInDeal


class DealListResponse(BaseModel):
    """Paginated list of deals."""

    items: list[DealResponse]
    total: int
    skip: int
    limit: int
