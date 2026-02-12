from pydantic import BaseModel, Field

from app.schemas.pagination import PaginatedResponse


class HotelResponse(BaseModel):
    """Single hotel."""

    model_config = {"from_attributes": True}

    id: int
    name: str
    city: str


HotelListResponse = PaginatedResponse[HotelResponse]


class HotelCreate(BaseModel):
    name: str = Field(max_length=200)
    city: str = Field(max_length=100)


class HotelUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=100)
