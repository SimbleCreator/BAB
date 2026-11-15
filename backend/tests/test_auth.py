import pytest
from sqlalchemy import select, text

from app.cli import main as cli_main
from app.core.cookies import REFRESH_COOKIE
from app.models import User
from tests.helpers import PASSWORD, bearer, register

pytestmark = pytest.mark.anyio

REG = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
CHANGE = "/api/v1/auth/change-password"


def _reg_body(**over):
    body = {
        "email": "a@example.com",
        "password": PASSWORD,
        "is_adult": True,
        "accepts_privacy": True,
    }
    return body | over


# Registration ---------------------------------------------------------------


async def test_register_returns_token_and_secure_cookie(client, session):
    r = await client.post(REG, json=_reg_body(email="  Asha@Example.COM "))
    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "asha@example.com"
    assert body["user"]["has_profile"] is False
    cookie = r.headers["set-cookie"].lower()
    for part in ("httponly", "secure", "samesite=lax", "path=/api/v1/auth"):
        assert part in cookie
    user = await session.scalar(select(User))
    assert user.password_hash.startswith("$argon2")
    assert user.consent_at is not None


@pytest.mark.parametrize(
    "over",
    [
        {"is_adult": False},
        {"accepts_privacy": False},
        {"password": "short"},
        {"email": "not-an-email"},
    ],
)
async def test_register_validation(client, over):
    r = await client.post(REG, json=_reg_body(**over))
    assert r.status_code == 422


async def test_register_password_minimum_is_ten(client):
    assert (await client.post(REG, json=_reg_body(password="x" * 9))).status_code == 422
    assert (await client.post(REG, json=_reg_body(password="x" * 10))).status_code == 201


async def test_register_duplicate_email_case_insensitive(client):
    await register(client, "a@example.com")
    r = await client.post(REG, json=_reg_body(email="A@EXAMPLE.com"))
    assert r.status_code == 409
    assert r.json()["code"] == "email_taken"


# Login ----------------------------------------------------------------------


async def test_login_ok_and_wrong_password_same_message_as_unknown(client):
    await register(client)
    ok = await client.post(LOGIN, json={"email": "A@example.com", "password": PASSWORD})
    assert ok.status_code == 200
    wrong = await client.post(LOGIN, json={"email": "a@example.com", "password": "nope-nope-1"})
    unknown = await client.post(LOGIN, json={"email": "x@example.com", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["detail"] == unknown.json()["detail"]


async def test_login_disabled_account(client, session):
    await register(client)
    await session.execute(text("UPDATE users SET is_active = false"))
    await session.commit()
    r = await client.post(LOGIN, json={"email": "a@example.com", "password": PASSWORD})
    assert r.status_code == 401
    assert r.json()["code"] == "account_disabled"


async def test_login_rate_limited(client):
    for _ in range(10):
        await client.post(LOGIN, json={"email": "x@example.com", "password": "whatever-1"})
    r = await client.post(LOGIN, json={"email": "x@example.com", "password": "whatever-1"})
    assert r.status_code == 429


async def test_register_rate_limited(client):
    for i in range(5):
        await client.post(REG, json=_reg_body(email=f"u{i}@example.com"))
    r = await client.post(REG, json=_reg_body(email="u9@example.com"))
    assert r.status_code == 429


# Access token -----------------------------------------------------------------


async def test_me_requires_valid_token(client):
    assert (await client.get(ME)).status_code == 401
    bad = await client.get(ME, headers={"Authorization": "Bearer garbage"})
    assert bad.status_code == 401
    tok = await register(client)
    r = await client.get(ME, headers=bearer(tok))
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"


# Refresh rotation ---------------------------------------------------------------


async def test_refresh_rotates_cookie(client):
    await register(client)
    first = client.cookies.get(REFRESH_COOKIE, path="/api/v1/auth")
    r = await client.post(REFRESH)
    assert r.status_code == 200
    second = client.cookies.get(REFRESH_COOKIE, path="/api/v1/auth")
    assert first != second
    assert (await client.get(ME, headers=bearer(r.json()))).status_code == 200


async def test_refresh_reuse_revokes_all_sessions(client, make_client):
    await register(client)
    stolen = client.cookies.get(REFRESH_COOKIE, path="/api/v1/auth")
    assert (await client.post(REFRESH)).status_code == 200  # legit rotation

    attacker = make_client()
    attacker.cookies.set(REFRESH_COOKIE, stolen, domain="test.local", path="/api/v1/auth")
    r = await attacker.post(REFRESH)
    assert r.status_code == 401
    assert r.json()["code"] == "refresh_reused"
    # The legitimate, newest token is now revoked too.
    assert (await client.post(REFRESH)).status_code == 401


async def test_refresh_without_cookie(client):
    r = await client.post(REFRESH)
    assert r.status_code == 401


async def test_logout_revokes_refresh(client):
    await register(client)
    token = client.cookies.get(REFRESH_COOKIE, path="/api/v1/auth")
    r = await client.post(LOGOUT)
    assert r.status_code == 204
    client.cookies.set(REFRESH_COOKIE, token, domain="test.local", path="/api/v1/auth")
    r = await client.post(REFRESH)
    assert r.status_code == 401


# Change password ----------------------------------------------------------------


async def test_change_password(client, make_client):
    tok = await register(client)
    other_device = make_client()
    await other_device.post(LOGIN, json={"email": "a@example.com", "password": PASSWORD})

    wrong = await client.post(
        CHANGE,
        json={"current_password": "wrong-pass-1", "new_password": "new-password-1"},
        headers=bearer(tok),
    )
    assert wrong.status_code == 400

    ok = await client.post(
        CHANGE,
        json={"current_password": PASSWORD, "new_password": "new-password-1"},
        headers=bearer(tok),
    )
    assert ok.status_code == 200
    # This device keeps a working session; the other device is signed out.
    assert (await client.post(REFRESH)).status_code == 200
    assert (await other_device.post(REFRESH)).status_code == 401
    old = await client.post(LOGIN, json={"email": "a@example.com", "password": PASSWORD})
    assert old.status_code == 401
    new = await client.post(LOGIN, json={"email": "a@example.com", "password": "new-password-1"})
    assert new.status_code == 200


async def test_production_refuses_weak_secret(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setenv("BAB_ENV", "production")
    monkeypatch.delenv("BAB_JWT_SECRET", raising=False)
    with pytest.raises(ValueError, match="BAB_JWT_SECRET"):
        Settings(_env_file=None)
    monkeypatch.setenv("BAB_JWT_SECRET", "x" * 40)
    assert Settings(_env_file=None).is_production


# CLI ----------------------------------------------------------------------------


async def test_cli_reset_password_and_make_admin(client, sessionmaker, monkeypatch, capsys):
    import asyncio

    import app.cli as cli

    await register(client)
    monkeypatch.setattr(cli, "SessionLocal", sessionmaker)

    loop = asyncio.get_running_loop()
    code = await loop.run_in_executor(
        None, cli_main, ["reset-password", "A@example.com", "--generate"]
    )
    assert code == 0
    new_password = capsys.readouterr().out.strip().splitlines()[-1].split(": ", 1)[1]
    assert (await client.post(REFRESH)).status_code == 401  # sessions ended
    r = await client.post(LOGIN, json={"email": "a@example.com", "password": new_password})
    assert r.status_code == 200

    code = await loop.run_in_executor(None, cli_main, ["make-admin", "a@example.com"])
    assert code == 0
    me = await client.get(ME, headers=bearer(r.json()))
    assert me.json()["is_admin"] is True

    code = await loop.run_in_executor(None, cli_main, ["make-admin", "nobody@example.com"])
    assert code == 1
