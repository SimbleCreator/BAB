import pytest

from app.content import exercise_library
from app.engines import adjustment_engine as eng
from app.engines import training_engine as te

LIB = exercise_library()
BY_CODE = LIB.by_code()


def test_weekly_change_pct():
    assert eng.weekly_change_pct(80, 79.2, 7) == pytest.approx(-1.0)
    assert eng.weekly_change_pct(80, 79.6, 14) == pytest.approx(-0.25)  # scaled to a week
    with pytest.raises(ValueError):
        eng.weekly_change_pct(80, 79, 0)


@pytest.mark.parametrize(
    ("goal", "pct", "delta"),
    [
        # lose fat: loss under 0.25% -> -100; loss over 1% -> +150; between -> 0
        ("lose_fat", -0.24, -100),
        ("lose_fat", 0.3, -100),  # gaining is also "under"
        ("lose_fat", -0.25, 0),
        ("lose_fat", -1.0, 0),
        ("lose_fat", -1.01, 150),
        # build muscle: gain under 0.1% -> +100; gain over 0.5% -> -100
        ("build_muscle", 0.09, 100),
        ("build_muscle", -0.2, 100),
        ("build_muscle", 0.1, 0),
        ("build_muscle", 0.5, 0),
        ("build_muscle", 0.51, -100),
        # stay fit: beyond 0.5% either way -> 100 toward stable
        ("stay_fit", 0.51, -100),
        ("stay_fit", -0.51, 100),
        ("stay_fit", 0.5, 0),
        ("stay_fit", -0.5, 0),
        ("stay_fit", 0.0, 0),
    ],
)
def test_nutrition_thresholds(goal, pct, delta):
    d = eng.nutrition_decision(goal, pct, 2000, 1500)
    assert d.new_kcal == 2000 + delta
    assert not d.floor_applied
    assert d.reason


def test_floor_is_respected():
    d = eng.nutrition_decision("lose_fat", 0.0, 1250, 1200)
    assert d.requested_kcal == 1150
    assert d.new_kcal == 1200 and d.floor_applied
    assert "1200" in d.reason


def inp(**over) -> te.TrainingInput:
    return te.TrainingInput(
        **(
            dict(
                goal="stay_fit",
                level="intermediate",
                minutes_per_day=30,
                days_per_week=3,
                has_pullup_bar=False,
            )
            | over
        )
    )


def sessions(**over) -> tuple[te.SessionPlan, ...]:
    return te.build_week(inp(**over), LIB.exercises, LIB.warmup, LIB.cooldown).sessions


@pytest.mark.parametrize(
    ("planned", "done", "decision"),
    [
        (0, 0, "no_data"),
        (5, 4, "progress"),
        (4, 4, "progress"),
        (5, 3, "unchanged"),
        (4, 2, "unchanged"),
        (5, 2, "reduce"),
        (3, 0, "reduce"),
    ],
)
def test_training_decision_thresholds(planned, done, decision):
    assert eng.training_decision(eng.LastWeek(planned, done, {})) == decision


def test_progress_adds_reps_only_for_exercises_that_met_targets():
    s = sessions()
    first, second = s[0].exercises[0], s[0].exercises[1]
    week = eng.LastWeek(3, 3, {first.code: True, second.code: False})
    out = eng.apply_training(s, week, BY_CODE, inp())
    p1 = out.sessions[0].exercises[0]
    p2 = out.sessions[0].exercises[1]
    if first.target_reps is not None:
        assert p1.target_reps == min(first.reps_max, first.target_reps + 2)
    else:
        assert p1.target_seconds == min(first.seconds_max, first.target_seconds + 5)
    assert p2 == second
    assert out.decision == "progress" and out.changes


def test_progress_caps_at_range_top_then_moves_harder():
    p = te.Prescription("pushup", 3, 60, reps_min=10, reps_max=12, target_reps=11)
    s = (te.SessionPlan(0, "full", "Full body", ("push",), (), (p,), None, (), 30),)
    week = eng.LastWeek(1, 1, {"pushup": True})
    once = eng.apply_training(s, week, BY_CODE, inp())
    assert once.sessions[0].exercises[0].target_reps == 12  # capped at range top
    twice = eng.apply_training(once.sessions, week, BY_CODE, inp())
    harder = twice.sessions[0].exercises[0]
    assert harder.code == BY_CODE["pushup"].harder
    assert harder.target_reps == harder.reps_min and harder.sets == 3
    assert "to" in twice.changes[0]


def test_no_harder_move_onto_a_bar_without_one():
    p = te.Prescription("scapular_pullup", 3, 60, reps_min=10, reps_max=12, target_reps=12)
    s = (te.SessionPlan(0, "pull", "Pull", ("pull",), (), (p,), None, (), 30),)
    out = eng.apply_training(s, eng.LastWeek(1, 1, {"scapular_pullup": True}), BY_CODE, inp())
    assert out.sessions[0].exercises[0] == p
    assert out.changes == ()


def test_timed_progress_by_seconds():
    p = te.Prescription("forearm_plank", 3, 60, seconds_min=30, seconds_max=50, target_seconds=30)
    s = (te.SessionPlan(0, "full", "Full body", ("core",), (), (p,), None, (), 30),)
    out = eng.apply_training(s, eng.LastWeek(1, 1, {"forearm_plank": True}), BY_CODE, inp())
    assert out.sessions[0].exercises[0].target_seconds == 35


def test_reduce_removes_one_set_never_below_one():
    s = sessions()
    out = eng.apply_training(s, eng.LastWeek(3, 1, {}), BY_CODE, inp())
    for before, after in zip(s, out.sessions, strict=True):
        for a, b in zip(before.exercises, after.exercises, strict=True):
            assert b.sets == max(1, a.sets - 1)
    one = (
        te.SessionPlan(
            0,
            "full",
            "F",
            ("push",),
            (),
            (te.Prescription("pushup", 1, 60, 10, 12, 10),),
            None,
            (),
            10,
        ),
    )
    assert (
        eng.apply_training(one, eng.LastWeek(3, 0, {}), BY_CODE, inp())
        .sessions[0]
        .exercises[0]
        .sets
        == 1
    )


def test_unchanged_and_no_data_keep_sessions():
    s = sessions()
    assert eng.apply_training(s, eng.LastWeek(4, 2, {}), BY_CODE, inp()).sessions == s
    assert eng.apply_training(s, eng.LastWeek(0, 0, {}), BY_CODE, inp()).sessions == s


def test_summary_text():
    week = eng.LastWeek(4, 2, {})
    res = eng.apply_training(sessions(), week, BY_CODE, inp())
    assert "2 of 4" in eng.training_summary(week, res)
