from httpx import AsyncClient


async def test_health_ok(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "app" in body
    assert "version" in body


async def test_v1_ping(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/ping")
    assert resp.status_code == 200
    assert resp.json() == {"pong": "ok"}
