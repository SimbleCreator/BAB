from datetime import timedelta

import pytest

from app.core.timeutil import local_today
from tests.helpers import PROFILE, bearer, onboard, register

pytestmark = pytest.mark.anyio

TZ = PROFILE["timezone"]
URL = "/api/v1/activity"


def today():
    return local_today(TZ)


async def test_requires_profile(client):
    h = bearer(await register(client))
    r = await client.put(f"{URL}/{today()}", json={"steps": 100}, headers=h)
    assert r.status_code == 409
    assert r.json()["code"] == "profile_missing"


async def test_save_get_update_delete(client):
    h = await onboard(client)  # 162 cm, 64.5 kg
    day = today()
    r = await client.put(f"{URL}/{day}", json={"steps": 10000, "note": " evening walk "}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "manual"
    assert body["note"] == "evening walk"
    assert body["distance_m"] == round(10000 * 162 * 0.415 / 100)
    assert body["distance_estimated"] is True
    assert body["active_kcal"] == round(10000 * 0.04 * 64.5 / 70)
    assert body["active_kcal_estimated"] is True

    r = await client.put(
        f"{URL}/{day}", json={"steps": 12000, "distance_m": 9100, "active_kcal": 500}, headers=h
    )
    assert r.json()["distance_estimated"] is False
    assert (await client.get(f"{URL}/{day}", headers=h)).json()["steps"] == 12000

    assert (await client.delete(f"{URL}/{day}", headers=h)).status_code == 204
    assert (await client.get(f"{URL}/{day}", headers=h)).status_code == 404
    assert (await client.delete(f"{URL}/{day}", headers=h)).status_code == 404


async def test_past_days_allowed_future_rejected(client):
    h = await onboard(client)
    past = today() - timedelta(days=40)
    assert (await client.put(f"{URL}/{past}", json={"steps": 1}, headers=h)).status_code == 200
    future = today() + timedelta(days=1)
    r = await client.put(f"{URL}/{future}", json={"steps": 1}, headers=h)
    assert r.status_code == 400
    assert r.json()["code"] == "future_day"


@pytest.mark.parametrize(
    "body",
    [{}, {"note": "only a note"}, {"steps": -1}, {"steps": 200_001}, {"distance_m": 300_001}],
)
async def test_validation(client, body):
    h = await onboard(client)
    assert (await client.put(f"{URL}/{today()}", json=body, headers=h)).status_code == 422


async def test_list_range(client):
    h = await onboard(client)
    t = today()
    for i in (0, 3, 10):
        await client.put(f"{URL}/{t - timedelta(days=i)}", json={"steps": 1000 + i}, headers=h)
    r = await client.get(URL, params={"from": str(t - timedelta(days=5)), "to": str(t)}, headers=h)
    assert [d["steps"] for d in r.json()] == [1003, 1000]
    bad = await client.get(
        URL, params={"from": str(t), "to": str(t - timedelta(days=1))}, headers=h
    )
    assert bad.status_code == 400
    long = await client.get(
        URL, params={"from": str(t - timedelta(days=400)), "to": str(t)}, headers=h
    )
    assert long.status_code == 400


async def test_summary_series_and_streak(client):
    h = await onboard(client, daily_step_goal=5000)
    t = today()
    for i, steps in [(0, 6000), (1, 5000), (2, 7000), (4, 9000), (5, 100)]:
        await client.put(f"{URL}/{t - timedelta(days=i)}", json={"steps": steps}, headers=h)
    s = (await client.get(f"{URL}/summary", params={"days": 7}, headers=h)).json()
    assert s["today"] == str(t)
    assert s["step_goal"] == 5000
    assert s["current_streak"] == 3
    assert s["longest_streak"] == 3
    assert len(s["days"]) == 7
    assert s["days"][-1]["day"] == str(t)
    assert s["days"][-1]["goal_met"] is True
    assert s["days"][-4]["has_entry"] is False  # 3 days ago
    assert s["total_steps"] == 6000 + 5000 + 7000 + 9000 + 100


async def test_today_endpoint(client):
    h = await onboard(client)
    r = (await client.get("/api/v1/today", headers=h)).json()
    assert r["day"] == str(today())
    assert r["name"] == PROFILE["name"]
    assert r["line"]
    assert r["activity"] is None
    await client.put(f"{URL}/{today()}", json={"steps": 9000}, headers=h)
    r = (await client.get("/api/v1/today", headers=h)).json()
    assert r["activity"]["steps"] == 9000
    assert r["current_streak"] == 1


async def test_csv_template_download(client):
    r = await client.get(f"{URL}/csv-template")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert r.text.startswith("date,steps,distance_km,active_kcal")


def _csv(*rows: str) -> dict:
    content = "date,steps,distance_km,active_kcal\n" + "\n".join(rows) + "\n"
    return {"file": ("a.csv", content.encode(), "text/csv")}


async def test_csv_preview_and_import_with_overwrite(client):
    h = await onboard(client)
    t = today()
    d1, d2, d3 = (str(t - timedelta(days=i)) for i in (1, 2, 3))
    await client.put(f"{URL}/{d1}", json={"steps": 111, "note": "keep me"}, headers=h)
    files = _csv(f"{d1},8000,6,300", f"{d2},9000,,", f"{d3},abc,,", f"{t + timedelta(days=1)},1,,")

    p = (await client.post(f"{URL}/import/preview", files=files, headers=h)).json()
    assert (p["valid_rows"], p["invalid_rows"], p["existing_rows"]) == (2, 2, 1)
    assert p["rows"][0]["exists"] is True
    assert p["rows"][0]["distance_m"] == 6000

    r = await client.post(f"{URL}/import", files=files, data={"overwrite": "false"}, headers=h)
    assert r.json() == {"created": 1, "updated": 0, "skipped_existing": 1, "skipped_invalid": 2}
    assert (await client.get(f"{URL}/{d1}", headers=h)).json()["steps"] == 111

    r = await client.post(f"{URL}/import", files=files, data={"overwrite": "true"}, headers=h)
    assert r.json() == {"created": 0, "updated": 2, "skipped_existing": 0, "skipped_invalid": 2}
    row = (await client.get(f"{URL}/{d1}", headers=h)).json()
    assert (row["steps"], row["source"], row["note"]) == (8000, "csv", "keep me")


async def test_csv_bad_file(client):
    h = await onboard(client)
    files = {"file": ("a.csv", b"hello,world\n1,2\n", "text/csv")}
    p = (await client.post(f"{URL}/import/preview", files=files, headers=h)).json()
    assert p["file_errors"]
    r = await client.post(f"{URL}/import", files=files, headers=h)
    assert r.status_code == 400
    big = {"file": ("a.csv", b"x" * (1024 * 1024 + 10), "text/csv")}
    p = (await client.post(f"{URL}/import/preview", files=big, headers=h)).json()
    assert p["file_errors"] == ["File is larger than 1 MB."]


async def test_isolation_between_users(client, make_client):
    ha = await onboard(client, "a@example.com")
    other = make_client()
    hb = await onboard(other, "b@example.com")
    day = str(today())
    await client.put(f"{URL}/{day}", json={"steps": 1111}, headers=ha)
    await other.put(f"{URL}/{day}", json={"steps": 2222}, headers=hb)

    # Same day for both users: each sees only their own.
    assert (await client.get(f"{URL}/{day}", headers=ha)).json()["steps"] == 1111
    assert (await other.get(f"{URL}/{day}", headers=hb)).json()["steps"] == 2222
    # A deletes their day; B's is untouched.
    await client.delete(f"{URL}/{day}", headers=ha)
    assert (await other.get(f"{URL}/{day}", headers=hb)).json()["steps"] == 2222
    # Lists, summaries and Today never include the other user's data.
    rng = {"from": day, "to": day}
    assert (await client.get(URL, params=rng, headers=ha)).json() == []
    s = (await client.get(f"{URL}/summary", params={"days": 1}, headers=ha)).json()
    assert s["total_steps"] == 0
    assert (await client.get("/api/v1/today", headers=ha)).json()["activity"] is None
    # A's CSV import does not touch B's day.
    await client.post(
        f"{URL}/import", files=_csv(f"{day},5,,"), data={"overwrite": "true"}, headers=ha
    )
    assert (await other.get(f"{URL}/{day}", headers=hb)).json()["steps"] == 2222
