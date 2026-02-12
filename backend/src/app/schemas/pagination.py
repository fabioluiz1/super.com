"""Generic pagination types shared by all list endpoints.

PaginatedResponse[T] — Pydantic model for HTTP responses (serializable).
Paginated[T]         — plain dataclass for service-layer returns (not serializable).
"""

from dataclasses import dataclass

from pydantic import BaseModel


class PaginatedResponse[T](BaseModel):
    """Pydantic model for paginated HTTP responses.

    Inherits BaseModel so FastAPI can serialize it to JSON and validate
    ``response_model`` automatically. ``from_attributes`` is set so
    ``model_validate`` can read attributes directly from a ``Paginated``
    dataclass without extra kwargs. ``[T]`` is a Python 3.12 type parameter
    — it lets you reuse this class for any entity without subclassing::

        # schemas/deal.py
        DealListResponse = PaginatedResponse[DealResponse]

    Use this in **routers** (the HTTP boundary). Don't use it inside services
    or repositories — those layers shouldn't depend on Pydantic.
    """

    model_config = {"from_attributes": True}

    items: list[T]
    total: int
    skip: int
    limit: int


@dataclass
class Paginated[T]:
    """Plain dataclass for paginated results inside the service layer.

    A dataclass instead of a Pydantic model because services shouldn't
    know about serialization — they just pass data up to the router.
    ``[T]`` is a Python 3.12 type parameter, so mypy checks the item type::

        # services/deal.py
        async def get_deals(db, skip, limit) -> Paginated[Deal]:
            items = await list_deals(db, skip, limit)
            total = await count_deals(db)
            return Paginated(items=items, total=total, skip=skip, limit=limit)

    The router then converts it to the Pydantic version for the response::

        result = await get_deals(db, skip, limit)
        return DealListResponse.model_validate(result)
    """

    items: list[T]
    total: int
    skip: int
    limit: int
