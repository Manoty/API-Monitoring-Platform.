import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


VALID_ENDPOINT_PAYLOAD = {
    "name": "Test API",
    "url": "https://httpbin.org/get",
    "method": "GET",
    "headers": {},
    "expected_status_code": 200,
    "interval_seconds": 60,
    "timeout_seconds": 10,
    "latency_threshold_ms": 2000.0,
    "max_consecutive_failures": 3,
}


async def test_create_endpoint(client: AsyncClient):
    response = await client.post("/api/v1/endpoints/", json=VALID_ENDPOINT_PAYLOAD)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test API"
    assert data["url"] == "https://httpbin.org/get"
    assert data["status"] == "active"
    assert "id" in data


async def test_list_endpoints_empty(client: AsyncClient):
    response = await client.get("/api/v1/endpoints/")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


async def test_list_endpoints_after_create(client: AsyncClient):
    await client.post("/api/v1/endpoints/", json=VALID_ENDPOINT_PAYLOAD)
    await client.post("/api/v1/endpoints/", json={**VALID_ENDPOINT_PAYLOAD, "name": "Second API"})

    response = await client.get("/api/v1/endpoints/")
    data = response.json()

    assert data["total"] == 2
    assert len(data["items"]) == 2


async def test_get_endpoint_by_id(client: AsyncClient):
    create_resp = await client.post("/api/v1/endpoints/", json=VALID_ENDPOINT_PAYLOAD)
    endpoint_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/endpoints/{endpoint_id}")

    assert response.status_code == 200
    assert response.json()["id"] == endpoint_id


async def test_get_endpoint_not_found(client: AsyncClient):
    response = await client.get("/api/v1/endpoints/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_update_endpoint(client: AsyncClient):
    create_resp = await client.post("/api/v1/endpoints/", json=VALID_ENDPOINT_PAYLOAD)
    endpoint_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/endpoints/{endpoint_id}",
        json={"name": "Updated Name", "interval_seconds": 120},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["interval_seconds"] == 120


async def test_pause_endpoint(client: AsyncClient):
    create_resp = await client.post("/api/v1/endpoints/", json=VALID_ENDPOINT_PAYLOAD)
    endpoint_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/endpoints/{endpoint_id}",
        json={"status": "paused"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "paused"


async def test_delete_endpoint(client: AsyncClient):
    create_resp = await client.post("/api/v1/endpoints/", json=VALID_ENDPOINT_PAYLOAD)
    endpoint_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/endpoints/{endpoint_id}")
    assert delete_resp.status_code == 204

    # confirm it's gone
    get_resp = await client.get(f"/api/v1/endpoints/{endpoint_id}")
    assert get_resp.status_code == 404


async def test_create_endpoint_invalid_url(client: AsyncClient):
    response = await client.post(
        "/api/v1/endpoints/",
        json={**VALID_ENDPOINT_PAYLOAD, "url": "not-a-url"},
    )
    assert response.status_code == 422


async def test_create_endpoint_invalid_interval(client: AsyncClient):
    # interval below minimum of 10s
    response = await client.post(
        "/api/v1/endpoints/",
        json={**VALID_ENDPOINT_PAYLOAD, "interval_seconds": 5},
    )
    assert response.status_code == 422