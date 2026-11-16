from datetime import timedelta

import pytest

from app.core.timeutil import local_today
from tests.helpers import PROFILE, onboard

pytestmark = pytest.mark.anyio

URL = "/api/v1/progress"


def day(n: int) -> str:
    return str(local_today(PROFILE["timezone"]) - timedelta(days=n))


async def test_projection_needs_a_target(client):
    h = await onboard(client)
    p = (await client.get(URL, headers=h)).json()
    assert p["projection"]["status"] == "no_target"
    assert p["cards"] == [] and p["next_card_on"] is None


async def test_formula_projection_from_profile(client):
    # Female 30, 162 cm, 64.5 kg, lose fat: maintenance 2087, target 1687, gap 400.
    h = await onboard(client, target_weight_kg=60)
    pr = (await client.get(URL, headers=h)).json()["projection"]
    assert pr["status"] == "on_track" and pr["method"] == "formula"
    assert pr["daily_gap_kcal"] == 400
    assert pr["kg_to_go"] == -4.5
    # 400*7/7700 = 0.364 kg a week; 4.5/0.436 = 10.3 -> 11, 4.5/0.291 = 15.5 -> 16.
    assert (pr["weeks_min"], pr["weeks_max"]) == (11, 16)
    assert pr["checkins_for_trend"] == 3
    assert pr["safe_rate_kg"] == 0.65


async def test_checkin_wins_trend_and_cards(client):
    h = await onboard(client, target_weight_kg=60)
    for n, kg, energy in ((35, 66, 2), (21, 65.5, None), (10, 65, 3), (0, 64.5, 4)):
        body = {"weight_kg": kg, "energy": energy, "stairs": 3}
        r = await client.put(f"/api/v1/checkins/{day(n)}", json=body, headers=h)
        assert r.status_code == 200, r.text
    listed = (await client.get("/api/v1/checkins", headers=h)).json()
    assert listed[0]["energy"] == 4 and listed[0]["stairs"] == 3 and listed[0]["sleep"] is None

    p = (await client.get(URL, headers=h)).json()
    pr = p["projection"]
    assert pr["method"] == "trend" and pr["checkins_for_trend"] == 0
    assert pr["weekly_rate_kg"] < 0
    [card] = p["cards"]
    assert card["number"] == 1 and card["then_day"] == day(35)
    assert {"name": "energy", "then": 2, "now": 3, "change": 1} in card["wins"]
    assert card["highlights"][0] == "1 kg down since you started."
    assert p["next_card_on"] == day(35 - 56)


async def test_checkin_score_range(client):
    h = await onboard(client)
    for bad in (0, 6):
        r = await client.put(
            f"/api/v1/checkins/{day(0)}", json={"weight_kg": 64, "sleep": bad}, headers=h
        )
        assert r.status_code == 422


async def test_progress_is_per_user(client):
    a = await onboard(client, target_weight_kg=60)
    await client.put(f"/api/v1/checkins/{day(40)}", json={"weight_kg": 70}, headers=a)
    b = await onboard(client, "b@example.com")
    p = (await client.get(URL, headers=b)).json()
    assert p["cards"] == [] and p["projection"]["status"] == "no_target"


async def test_target_weight_validation(client):
    h = await onboard(client)
    r = await client.put("/api/v1/profile", json=PROFILE | {"target_weight_kg": 20}, headers=h)
    assert r.status_code == 422
