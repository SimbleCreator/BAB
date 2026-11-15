from datetime import date

import pytest

from app.schemas.bounce import GymProfileIn, PlanContent
from app.services.bounce import rules
from app.services.bounce.llm import extract_json
from app.services.bounce.prompt import BounceContext, build_messages
from tests.bounce_helpers import plan_dict

D = date(2026, 11, 15)


def content(**kw) -> PlanContent:
    return PlanContent.model_validate(plan_dict(**kw))


@pytest.mark.parametrize(
    ("plan", "checkin", "today", "state"),
    [
        (None, None, D, "none"),
        (rules.PlanFacts(D, None, "activity"), None, date(2026, 11, 21), "active"),
        (rules.PlanFacts(D, None, "activity"), None, date(2026, 11, 22), "checkin_needed"),
        (rules.PlanFacts(D, D, "activity"), D, date(2026, 11, 22), "checkin_needed"),
        (rules.PlanFacts(D, D, "activity"), date(2026, 11, 22), date(2026, 11, 22), "update_ready"),
        (rules.PlanFacts(D, None, "gym"), date(2026, 11, 10), date(2026, 11, 30), "update_ready"),
    ],
)
def test_plan_state(plan, checkin, today, state):
    assert rules.plan_state(plan, checkin, today) == state


def test_veg_rejects_egg_and_meat_but_not_eggplant_or_negation():
    assert rules.diet_violations(content(meal="Chicken curry and boiled eggs"), "veg") == [
        "chicken",
        "eggs",
    ]
    assert rules.diet_violations(content(meal="Eggplant curry, no egg"), "veg") == []
    assert rules.diet_violations(content(meal="Egg-free cake"), "veg") == []


def test_egg_diet_allows_egg_not_fish():
    assert rules.diet_violations(content(meal="Omelette and toast"), "egg") == []
    assert rules.diet_violations(content(meal="Fish fry"), "egg") == ["fish"]
    assert rules.diet_violations(content(meal="Fish fry"), "non_veg") == []


def test_activity_mode_drops_gym_parts():
    out = rules.enforce_mode(content(), "activity")
    assert all(
        not d.gym_exercises and d.gym_focus is None and d.cardio_minutes == 0 for d in out.days
    )
    assert out.days[0].home_exercises


def test_gym_mode_drops_home_parts():
    out = rules.enforce_mode(content(), "gym")
    assert all(
        not d.home_exercises and d.walk_minutes == 0 and d.jog_minutes == 0 for d in out.days
    )
    assert out.days[0].gym_exercises


def test_both_mode_keeps_both():
    out = rules.enforce_mode(content(), "both")
    assert out.days[0].gym_exercises and out.days[0].home_exercises


def test_finalize_removes_banned_tips_and_adds_safety_lines():
    out = rules.finalize(content(), "gym", ["creatine", "fat_burner"])
    assert all("steroid" not in t.lower() for t in out.tips)
    assert out.supplements_advice[0] == rules.FAT_BURNER_WARNING
    assert rules.SUPPLEMENT_SAFETY in out.supplements_advice
    assert out.supplements_advice[-1] == rules.NEVER_SUGGEST


def test_activity_without_supplements_has_no_advice():
    assert rules.finalize(content(), "activity", []).supplements_advice == []


def test_days_must_be_in_order():
    p = plan_dict()
    p["days"][0], p["days"][1] = p["days"][1], p["days"][0]
    with pytest.raises(ValueError):
        PlanContent.model_validate(p)


def test_extract_json_handles_fences_and_thinking():
    assert extract_json('<think>{"x": 2}</think> ok ```json\n{"a": 1}\n```') == {"a": 1}
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_gym_profile_none_wins():
    g = GymProfileIn(
        experience="beginner",
        days_per_week=3,
        session_minutes=60,
        supplements=["creatine", "none", "creatine"],
    )
    assert g.supplements == ["none"]


def _ctx(**kw) -> BounceContext:
    base = dict(
        mode="activity",
        age=30,
        sex="female",
        height_cm=162,
        weight_kg=64.5,
        goal="lose_fat",
        level="beginner",
        minutes_per_day=30,
        days_per_week=3,
        diet_type="veg",
        daily_step_goal=8000,
        calories_kcal=1700,
        protein_g=116,
        carbs_g=180,
        fat_g=47,
    )
    return BounceContext(**(base | kw))


def test_prompt_carries_mode_diet_and_targets():
    msgs = build_messages(_ctx())
    text = msgs[0]["content"]
    assert "ACTIVITY only" in text and "no eggs" in text and '"calories_kcal": 1700' in text
    gym = build_messages(_ctx(mode="gym"))[0]["content"]
    assert "TRAIN only" in gym


def test_prompt_retry_explains_reason():
    msgs = build_messages(_ctx(), "it had chicken")
    assert len(msgs) == 3 and "it had chicken" in msgs[-1]["content"]


def test_lenient_lists_numbers_and_nulls():
    p = plan_dict()
    p["diet"]["eat_more"] = "Dal, sprouts, curd (low fat), fruit"
    p["tips"] = "Walk after dinner. Sleep 8 hours! Drink water"
    p["supplements_advice"] = None
    p["days"][0]["walk_minutes"] = 500
    p["days"][0]["jog_minutes"] = None
    p["days"][0]["home_exercises"][0]["sets"] = "4"
    p["days"][0]["home_exercises"][0]["name"] = "x" * 100
    c = PlanContent.model_validate(p)
    assert c.diet.eat_more == ["Dal", "sprouts", "curd (low fat)", "fruit"]
    assert c.tips == ["Walk after dinner", "Sleep 8 hours!", "Drink water"]
    assert c.supplements_advice == []
    assert c.days[0].walk_minutes == 180 and c.days[0].jog_minutes == 0
    assert c.days[0].home_exercises[0].sets == 4
    assert len(c.days[0].home_exercises[0].name) == 60


def test_lenient_types_still_reject_missing_parts():
    p = plan_dict()
    del p["diet"]["days"][3]["dinner"]
    with pytest.raises(ValueError):
        PlanContent.model_validate(p)


def test_openrouter_request_body():
    from app.services.bounce.llm import OpenAICompatibleClient

    msgs = [{"role": "user", "content": "hi"}]
    orc = OpenAICompatibleClient(
        "https://openrouter.ai/api/v1", "k", "a:free", 60, fallbacks=["b:free"]
    )
    body = orc.body(msgs, 100)
    assert body["models"] == ["a:free", "b:free"]
    assert body["reasoning"] == {"enabled": False}
    assert body["response_format"] == {"type": "json_object"}

    other = OpenAICompatibleClient("http://localhost:11434/v1", "k", "m", 60, json_mode=False)
    body = other.body(msgs, 100)
    assert "models" not in body and "reasoning" not in body and "response_format" not in body


def _nudge(hour=8, due=False, meals=(), steps=None, goal=8000):
    return rules.pick_nudge(D, hour, due, set(meals), steps, goal)


def test_nudge_checkin_comes_first():
    n = _nudge(hour=22, due=True)
    assert n.kind == "checkin" and n.id == "checkin:2026-11-15"


def test_nudge_meals_by_hour():
    assert _nudge(hour=9) is None
    assert _nudge(hour=10).id == "meals:2026-11-15:breakfast"
    assert _nudge(hour=15, meals={"breakfast"}).id == "meals:2026-11-15:lunch"
    # The latest missed meal is asked about.
    assert "lunch" in _nudge(hour=16).message
    assert _nudge(hour=21, meals={"breakfast", "lunch", "snack"}).id.endswith("dinner")


ALL = {"breakfast", "lunch", "snack", "dinner"}


def test_nudge_activity_checkup():
    assert _nudge(hour=11, meals={"breakfast"}) is None
    assert _nudge(hour=12, meals={"breakfast"}).kind == "activity"
    assert _nudge(hour=17, meals={"breakfast", "lunch"}, steps=3000) is None
    n = _nudge(hour=22, meals=ALL, steps=6500)
    assert n.id == "steps:2026-11-15" and "1,500 steps" in n.message
    assert _nudge(hour=22, meals=ALL, steps=9000) is None
