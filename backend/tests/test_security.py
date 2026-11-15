import httpx
import pytest

from app.core.config import Settings
from app.main import create_app
from tests.helpers import register

pytestmark = pytest.mark.anyio


async def test_security_headers(client):
    r = await client.get("/api/v1/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "default-src 'none'" in r.headers["content-security-policy"]


async def test_cookie_endpoints_need_client_header(make_client):
    c = make_client()
    await register(c)
    bare = httpx.AsyncClient(transport=c._transport, base_url="https://test", cookies=c.cookies)
    try:
        r = await bare.post("/api/v1/auth/refresh")
        assert r.status_code == 403 and r.json()["code"] == "client_header_missing"
        assert (await bare.post("/api/v1/auth/logout")).status_code == 403
    finally:
        await bare.aclose()
    assert (await c.post("/api/v1/auth/refresh")).status_code == 200


async def test_preflight_allows_client_header_only_for_frontend(client):
    ok = await client.options(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:4200",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-bab-client",
        },
    )
    assert ok.status_code == 200
    bad = await client.options(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-bab-client",
        },
    )
    assert bad.status_code == 400


async def test_oversized_body_rejected_before_reading(client):
    h = {"Content-Length": str(7 * 1024 * 1024), "Content-Type": "application/json"}
    r = await client.post("/api/v1/auth/login", content=b"{}", headers=h)
    assert r.status_code == 413


async def test_oversized_streamed_body_rejected(client):
    from tests.helpers import onboard

    h = await onboard(client)

    async def chunks():
        yield (
            b'--x\r\nContent-Disposition: form-data; name="file"; filename="a.gpx"\r\n'
            b"Content-Type: application/gpx+xml\r\n\r\n"
        )
        for _ in range(8):
            yield b"x" * (1024 * 1024)
        yield b"\r\n--x--\r\n"

    r = await client.post(
        "/api/v1/runs/gpx",
        content=chunks(),
        headers=h | {"Content-Type": "multipart/form-data; boundary=x"},
    )
    assert r.status_code == 413, r.text


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"BAB_JWT_SECRET": "x" * 40}, "BAB_DATABASE_URL"),
        (
            {
                "BAB_JWT_SECRET": "x" * 40,
                "BAB_DATABASE_URL": "postgresql+asyncpg://u:p@db/x",
                "BAB_FRONTEND_ORIGIN": "http://app.example.com",
            },
            "https",
        ),
    ],
)
def test_production_settings_are_strict(monkeypatch, env, message):
    monkeypatch.setenv("BAB_ENV", "production")
    for k in ("BAB_DATABASE_URL", "BAB_FRONTEND_ORIGIN"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ValueError, match=message):
        Settings(_env_file=None)


def test_production_hides_docs_and_schema(monkeypatch):
    import app.main as main

    monkeypatch.setattr(
        main,
        "get_settings",
        lambda: Settings(
            _env_file=None,
            env="production",
            jwt_secret="x" * 40,
            database_url="postgresql+asyncpg://u:p@db/x",
            frontend_origin="https://app.example.com",
        ),
    )
    app = create_app()
    assert app.docs_url is None and app.openapi_url is None
