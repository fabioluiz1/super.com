"""Integration tests for GET /deals endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_deals_returns_paginated_response(client: AsyncClient, seeded_db: None) -> None:
    resp = await client.get("/deals")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 7
    assert body["skip"] == 0
    assert body["limit"] == 20
    assert len(body["items"]) == 7


@pytest.mark.asyncio
async def test_list_deals_includes_nested_hotel(client: AsyncClient, seeded_db: None) -> None:
    resp = await client.get("/deals")
    item = resp.json()["items"][0]
    hotel = item["hotel"]
    assert "id" in hotel
    assert "name" in hotel
    assert "city" in hotel
    assert "country" in hotel
    assert "phone" in hotel
    assert "avg_rating" in hotel
    assert "created_at" in hotel
    assert "updated_at" in hotel


@pytest.mark.asyncio
async def test_list_deals_hotel_avg_rating_is_correct(client: AsyncClient, seeded_db: None) -> None:
    resp = await client.get("/deals")
    items = resp.json()["items"]

    # Build hotel avg_rating lookup from response (hotel name → avg_rating)
    hotel_ratings: dict[str, float] = {}
    for item in items:
        hotel_ratings[item["hotel"]["name"]] = item["hotel"]["avg_rating"]

    # Lakeside Court: ratings 5, 4, 3, 5 → avg 4.25
    assert hotel_ratings["Lakeside Court"] == pytest.approx(4.25)
    # Metro Tower: ratings 4, 3, 5 → avg 4.0
    assert hotel_ratings["Metro Tower"] == pytest.approx(4.0)


@pytest.mark.asyncio
async def test_list_deals_pagination_skip(client: AsyncClient, seeded_db: None) -> None:
    resp = await client.get("/deals", params={"skip": 5})
    body = resp.json()
    assert body["total"] == 7
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_list_deals_pagination_limit(client: AsyncClient, seeded_db: None) -> None:
    resp = await client.get("/deals", params={"limit": 3})
    body = resp.json()
    assert len(body["items"]) == 3


@pytest.mark.asyncio
async def test_list_deals_empty_database(client: AsyncClient) -> None:
    resp = await client.get("/deals")
    body = resp.json()
    assert resp.status_code == 200
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_list_deals_invalid_skip_returns_422(client: AsyncClient) -> None:
    resp = await client.get("/deals", params={"skip": -1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_deals_invalid_limit_returns_422(client: AsyncClient) -> None:
    resp = await client.get("/deals", params={"limit": 0})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_deals_limit_over_max_returns_422(client: AsyncClient) -> None:
    resp = await client.get("/deals", params={"limit": 101})
    assert resp.status_code == 422
