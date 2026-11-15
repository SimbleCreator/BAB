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


async def test_every_route_has_a_response_schema(client):
    schema = (await client.get("/openapi.json")).json()
    for path, ops in schema["paths"].items():
        for method, op in ops.items():
            ok = next(code for code in op["responses"] if code.startswith("2"))
            if ok == "204":
                continue
            content = op["responses"][ok].get("content", {})
            assert "application/json" in content, f"{method.upper()} {path} has no response model"
            assert content["application/json"]["schema"], f"{method.upper()} {path}"
