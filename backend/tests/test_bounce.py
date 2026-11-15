from datetime import timedelta

import pytest
from sqlalchemy import update

from app.core.config import get_settings
from app.core.timeutil import local_today
from app.models.bounce import BouncePlan
from app.services.bounce.llm import LLMError, get_llm
from tests.bounce_helpers import FakeLLM, plan_dict, reply
from tests.helpers import PROFILE, onboard

pytestmark = pytest.mark.anyio

GYM = {
    "experience": "beginner",
    "days_per_week": 3,
    "session_minutes": 60,
    "supplements": ["creatine", "fat_burner"],
    "supplements_note": "5 g a day",
}


def use(client, llm):
    client._transport.app.dependency_overrides[get_llm] = lambda: llm
    return llm


def today():
    return local_today(PROFILE["timezone"])


async def test_disabled_without_key(client):
    h = await onboard(client)
    use(client, None)
    s = (await client.get("/api/v1/bounce/status", headers=h)).json()
    assert s["enabled"] is False and s["state"] == "disabled"
    assert s["tips"]
    r = await client.post("/api/v1/bounce/plan", headers=h)
    assert r.status_code == 503 and r.json()["code"] == "bounce_disabled"


async def test_activity_plan_is_checked_and_stored(client):
    h = await onboard(client)
    llm = use(client, FakeLLM(reply()))
    assert (await client.get("/api/v1/bounce/plan", headers=h)).status_code == 404
    s = (await client.get("/api/v1/bounce/status", headers=h)).json()
    assert s["state"] == "none" and s["enabled"] and s["plans_left_today"] == 5
    assert s["can_generate"] is True

    r = await client.post("/api/v1/bounce/plan", headers=h)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["mode"] == "activity" and plan["model"] == "fake/model"
    days = plan["content"]["days"]
    assert all(d["gym_exercises"] == [] and d["cardio_minutes"] == 0 for d in days)
    assert all("steroid" not in t.lower() for t in plan["content"]["tips"])
    assert plan["content"]["supplements_advice"] == []
    targets = (await client.get("/api/v1/nutrition/targets", headers=h)).json()
    assert plan["targets"]["calories_kcal"] == targets["current"]["calories_kcal"]
    # The prompt carried the user's numbers.
    prompt = llm.calls[0][0]["content"]
    assert '"height_cm": 162.0' in prompt and '"minutes_per_day": 30' in prompt

    assert (await client.get("/api/v1/bounce/plan", headers=h)).json()["id"] == plan["id"]
    s = (await client.get("/api/v1/bounce/status", headers=h)).json()
    assert s["state"] == "active" and s["plans_left_today"] == 4
    assert s["can_generate"] is False
    assert s["next_update_on"] == (today() + timedelta(days=7)).isoformat()
    assert any(t.startswith("Today") for t in s["tips"])

    r = await client.post("/api/v1/bounce/plan", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "plan_current"


async def test_gym_mode_needs_gym_profile_and_analyses_supplements(client):
    h = await onboard(client, training_mode="gym", diet_type="non_veg")
    use(client, FakeLLM(reply(plan_dict(meal="Chicken and rice"))))
    s = (await client.get("/api/v1/bounce/status", headers=h)).json()
    assert s["gym_profile_needed"] is True and "gym" in s["message"]
    r = await client.post("/api/v1/bounce/plan", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "gym_profile_needed"

    assert (await client.get("/api/v1/bounce/gym-profile", headers=h)).status_code == 404
    r = await client.put("/api/v1/bounce/gym-profile", json=GYM, headers=h)
    assert r.status_code == 200 and r.json()["supplements"] == ["creatine", "fat_burner"]

    plan = (await client.post("/api/v1/bounce/plan", headers=h)).json()
    assert plan["mode"] == "gym"
    assert all(
        d["home_exercises"] == [] and d["walk_minutes"] == 0 for d in plan["content"]["days"]
    )
    advice = plan["content"]["supplements_advice"]
    assert advice[0].startswith("Fat burners are not recommended")
    assert "Creatine is well studied at 3-5 g a day." in advice


async def test_changing_mode_allows_a_rebuild(client):
    h = await onboard(client)
    use(client, FakeLLM(reply()))
    assert (await client.post("/api/v1/bounce/plan", headers=h)).status_code == 200
    await client.put("/api/v1/profile", json=PROFILE | {"training_mode": "both"}, headers=h)
    s = (await client.get("/api/v1/bounce/status", headers=h)).json()
    assert s["gym_profile_needed"] and s["can_generate"] is False
    assert "gym" in s["message"]
    await client.put("/api/v1/bounce/gym-profile", json=GYM | {"supplements": []}, headers=h)
    s = (await client.get("/api/v1/bounce/status", headers=h)).json()
    assert s["state"] == "active" and s["can_generate"] is True
    assert s["message"].startswith("Your details changed")
    plan = (await client.post("/api/v1/bounce/plan", headers=h)).json()
    assert plan["mode"] == "both"
    assert (
        plan["content"]["days"][0]["gym_exercises"] and plan["content"]["days"][0]["home_exercises"]
    )


async def test_diet_violation_is_retried_then_rejected(client):
    h = await onboard(client)  # veg
    llm = use(client, FakeLLM(reply(plan_dict(meal="Boiled eggs")), reply()))
    r = await client.post("/api/v1/bounce/plan", headers=h)
    assert r.status_code == 200 and len(llm.calls) == 2
    assert "eggs" in llm.calls[1][-1]["content"]

    h2 = await onboard(client, "b@example.com")
    use(client, FakeLLM(reply(plan_dict(meal="Chicken curry"))))
    r = await client.post("/api/v1/bounce/plan", headers=h2)
    assert r.status_code == 502 and r.json()["code"] == "model_bad_output"
    assert (await client.get("/api/v1/bounce/plan", headers=h2)).status_code == 404


async def test_bad_json_is_retried(client):
    h = await onboard(client)
    llm = use(client, FakeLLM("Sure! Here is a plan: walk a lot.", reply()))
    assert (await client.post("/api/v1/bounce/plan", headers=h)).status_code == 200
    assert len(llm.calls) == 2


async def test_model_errors_map_to_502(client):
    h = await onboard(client)
    use(client, FakeLLM(LLMError("Credits used up.", "model_credits")))
    r = await client.post("/api/v1/bounce/plan", headers=h)
    assert r.status_code == 502 and r.json()["code"] == "model_credits"


async def test_weekly_update_needs_a_new_checkin(client, session):
    h = await onboard(client)
    use(client, FakeLLM(reply()))
    plan = (await client.post("/api/v1/bounce/plan", headers=h)).json()
    await session.execute(
        update(BouncePlan)
        .where(BouncePlan.id == plan["id"])
        .values(created_at=BouncePlan.created_at - timedelta(days=8))
    )
    await session.commit()

    s = (await client.get("/api/v1/bounce/status", headers=h)).json()
    assert s["state"] == "checkin_needed" and "check-in" in s["message"]
    assert s["can_generate"] is False
    r = await client.post("/api/v1/bounce/plan", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "checkin_needed"

    day = today().isoformat()
    r = await client.put(f"/api/v1/checkins/{day}", json={"weight_kg": 63.8}, headers=h)
    assert r.status_code == 200, r.text
    assert (await client.get("/api/v1/bounce/status", headers=h)).json()["state"] == "update_ready"
    new = (await client.post("/api/v1/bounce/plan", headers=h)).json()
    assert new["id"] != plan["id"] and new["based_on_checkin_day"] == day


async def test_daily_limit(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_daily_plan_limit", 1)
    h = await onboard(client)
    use(client, FakeLLM(reply()))
    assert (await client.post("/api/v1/bounce/plan", headers=h)).status_code == 200
    await client.put("/api/v1/profile", json=PROFILE | {"goal": "stay_fit"}, headers=h)
    r = await client.post("/api/v1/bounce/plan", headers=h)
    assert r.status_code == 429


async def test_gym_profile_validation(client):
    h = await onboard(client)
    bad = GYM | {"session_minutes": 5, "supplements": ["steroids"]}
    assert (await client.put("/api/v1/bounce/gym-profile", json=bad, headers=h)).status_code == 422


async def test_training_mode_on_profile(client):
    h = await onboard(client)
    assert (await client.get("/api/v1/profile", headers=h)).json()["training_mode"] == "activity"
    r = await client.put("/api/v1/profile", json=PROFILE | {"training_mode": "gym"}, headers=h)
    assert r.json()["training_mode"] == "gym"
    bad = PROFILE | {"training_mode": "swim"}
    assert (await client.put("/api/v1/profile", json=bad, headers=h)).status_code == 422


async def test_users_cannot_see_each_others_bounce_data(make_client):
    a, b = make_client(), make_client()
    ha = await onboard(a, "a@example.com", training_mode="gym")
    hb = await onboard(b, "b@example.com")
    use(a, FakeLLM(reply()))
    use(b, FakeLLM(reply()))
    await a.put("/api/v1/bounce/gym-profile", json=GYM, headers=ha)
    assert (await a.post("/api/v1/bounce/plan", headers=ha)).status_code == 200

    assert (await b.get("/api/v1/bounce/plan", headers=hb)).status_code == 404
    assert (await b.get("/api/v1/bounce/gym-profile", headers=hb)).status_code == 404
    await b.put("/api/v1/bounce/gym-profile", json=GYM | {"days_per_week": 6}, headers=hb)
    assert (await a.get("/api/v1/bounce/gym-profile", headers=ha)).json()["days_per_week"] == 3
    assert (await b.get("/api/v1/bounce/status", headers=hb)).json()["state"] == "none"


async def test_export_includes_bounce_data(client):
    h = await onboard(client, training_mode="gym")
    use(client, FakeLLM(reply()))
    await client.put("/api/v1/bounce/gym-profile", json=GYM, headers=h)
    await client.post("/api/v1/bounce/plan", headers=h)
    data = (await client.get("/api/v1/account/export", headers=h)).json()
    assert data["gym_profile"]["supplements"] == ["creatine", "fat_burner"]
    assert len(data["bounce_plans"]) == 1 and data["bounce_plans"][0]["mode"] == "gym"


async def test_status_notification(client):
    h = await onboard(client)
    use(client, None)
    n = (await client.get("/api/v1/bounce/status", headers=h)).json()["notification"]
    # A new user has no check-in yet, which comes first.
    assert n["kind"] == "checkin" and n["id"] == f"checkin:{today().isoformat()}"
    await client.put(f"/api/v1/checkins/{today().isoformat()}", json={"weight_kg": 64}, headers=h)
    n = (await client.get("/api/v1/bounce/status", headers=h)).json()["notification"]
    assert n is None or n["kind"] in ("meals", "activity")
