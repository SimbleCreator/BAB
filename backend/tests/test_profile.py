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


# Personal B.A.B (M11): "Know me" -------------------------------------------------------

KNOW_ME = {
    "city": "  Bengaluru ",
    "state": "KA",
    "work_type": "desk",
    "food_source": "home",
    "wake_time": "06:30",
    "usual_foods": ["idli", "sambar", "idli"],
    "sleep_hours": 7.3,
    "sweet_drinks_per_day": 2,
    "fasting_note": " Ekadashi ",
    "food_budget_inr": 300,
}


async def test_know_me_fields_saved(client):
    from tests.helpers import onboard

    h = await onboard(client, **KNOW_ME)
    p = (await client.get("/api/v1/profile", headers=h)).json()
    assert p["city"] == "Bengaluru"
    assert p["region"] == "south"
    assert p["usual_foods"] == ["idli", "sambar"]
    assert p["sleep_hours"] == 7.5
    assert p["fasting_note"] == "Ekadashi"
    assert p["wake_time"] == "06:30"


async def test_know_me_optional_and_region_null_outside_india(client):
    from tests.helpers import onboard

    h = await onboard(client)
    p = (await client.get("/api/v1/profile", headers=h)).json()
    assert p["state"] is None and p["region"] is None and p["usual_foods"] == []
    h2 = await onboard(client, "b@example.com", state="OUT")
    assert (await client.get("/api/v1/profile", headers=h2)).json()["region"] is None


@pytest.mark.parametrize(
    "bad",
    [
        {"state": "ZZ"},
        {"wake_time": "6:30"},
        {"wake_time": "24:00"},
        {"usual_foods": ["not_a_food"]},
        {"usual_foods": [f"f{i}" for i in range(13)]},
        {"work_type": "astronaut"},
        {"sleep_hours": 2},
        {"food_budget_inr": 10},
    ],
)
async def test_know_me_validation(client, bad):
    from tests.helpers import PROFILE, bearer, register

    h = bearer(await register(client))
    r = await client.put("/api/v1/profile", json=PROFILE | bad, headers=h)
    assert r.status_code == 422


async def test_profile_options(client):
    from tests.helpers import bearer, register

    h = bearer(await register(client))
    o = (await client.get("/api/v1/profile/options", headers=h)).json()
    assert {"code": "KA", "name": "Karnataka", "region": "south"} in o["states"]
    assert o["states"][-1]["code"] == "OUT"
    assert o["work_types"] == ["desk", "standing", "physical", "shifts"]
    assert o["usual_foods_max"] == 12
