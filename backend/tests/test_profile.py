import pytest
from sqlalchemy import func, select, text

from app.models import Profile, RefreshToken
from tests.helpers import PROFILE, bearer, register

pytestmark = pytest.mark.anyio

URL = "/api/v1/profile"


async def test_profile_missing_then_created(client):
    tok = await register(client)
    h = bearer(tok)
    r = await client.get(URL, headers=h)
    assert r.status_code == 404
    assert r.json()["code"] == "profile_missing"

    r = await client.put(URL, json=PROFILE, headers=h)
    assert r.status_code == 200
    assert r.json()["weight_kg"] == 64.5
    assert (await client.get("/api/v1/auth/me", headers=h)).json()["has_profile"] is True

    r = await client.put(URL, json=PROFILE | {"weight_kg": 63.04, "goal": "stay_fit"}, headers=h)
    assert r.json()["weight_kg"] == 63.0
    assert r.json()["goal"] == "stay_fit"


async def test_profile_requires_auth(client):
    assert (await client.get(URL)).status_code == 401
    assert (await client.put(URL, json=PROFILE)).status_code == 401


@pytest.mark.parametrize(
    "over",
    [
        {"age": 17},
        {"timezone": "Mars/Base"},
        {"timezone": "../../etc/passwd"},
        {"days_per_week": 7},
        {"sex": "other"},
        {"goal": "get_huge"},
        {"diet_type": "vegan"},
        {"name": "   "},
        {"height_cm": 50},
    ],
)
async def test_profile_validation(client, over):
    tok = await register(client)
    r = await client.put(URL, json=PROFILE | over, headers=bearer(tok))
    assert r.status_code == 422


async def test_profile_isolation_between_users(client, make_client):
    a = await register(client, "a@example.com")
    other = make_client()
    b = await register(other, "b@example.com")

    await client.put(URL, json=PROFILE | {"name": "Asha"}, headers=bearer(a))
    await other.put(URL, json=PROFILE | {"name": "Bala"}, headers=bearer(b))

    # Each user only ever sees and changes their own profile.
    assert (await client.get(URL, headers=bearer(a))).json()["name"] == "Asha"
    await client.put(URL, json=PROFILE | {"name": "Changed"}, headers=bearer(a))
    assert (await other.get(URL, headers=bearer(b))).json()["name"] == "Bala"


async def test_deleting_user_cascades(client, session):
    tok = await register(client)
    await client.put(URL, json=PROFILE, headers=bearer(tok))
    await session.execute(text("DELETE FROM users"))
    await session.commit()
    assert await session.scalar(select(func.count()).select_from(Profile)) == 0
    assert await session.scalar(select(func.count()).select_from(RefreshToken)) == 0
