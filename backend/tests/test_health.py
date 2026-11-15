import pytest

pytestmark = pytest.mark.anyio


async def test_health_ok(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_cors_allows_configured_origin_only(client):
    allowed = await client.get("/api/v1/health", headers={"Origin": "http://localhost:4200"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:4200"
    other = await client.get("/api/v1/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in other.headers


async def test_openapi_has_response_model(client):
    schema = (await client.get("/openapi.json")).json()
    ok = schema["paths"]["/api/v1/health"]["get"]["responses"]["200"]
    assert ok["content"]["application/json"]["schema"]["$ref"].endswith("/HealthOut")
