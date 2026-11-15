import pytest

from app.content import exercise_library
from app.engines import training_engine as eng

LIB = exercise_library()
BY_CODE = LIB.by_code()


def inp(**over) -> eng.TrainingInput:
    base = dict(
        goal="stay_fit",
        level="intermediate",
        minutes_per_day=40,
        days_per_week=3,
        has_pullup_bar=False,
    )
    return eng.TrainingInput(**(base | over))


def build(**over) -> eng.WeekPlan:
    return eng.build_week(inp(**over), LIB.exercises, LIB.warmup, LIB.cooldown)


def main_exercises(plan: eng.WeekPlan) -> list[eng.Exercise]:
    return [BY_CODE[p.code] for s in plan.sessions for p in s.exercises]


def test_library_size_and_shape():
    assert len(LIB.exercises) >= 40
    assert {e.group for e in LIB.exercises} == {"push", "pull", "legs", "core", "cardio"}


@pytest.mark.parametrize(
    ("minutes", "count"), [(15, 4), (20, 4), (30, 5), (40, 6), (50, 7), (60, 8), (90, 8)]
)
def test_exercise_count_fits_minutes(minutes, count):
    assert eng.exercise_count(minutes) == count
    plan = build(minutes_per_day=minutes)
    assert all(len(s.exercises) == count for s in plan.sessions)


@pytest.mark.parametrize(
    ("days", "split", "kinds", "offsets"),
    [
        (2, "Full body", ["full"] * 2, [0, 3]),
        (3, "Full body", ["full"] * 3, [0, 2, 4]),
        (4, "Upper / lower", ["upper", "lower", "upper", "lower"], [0, 1, 3, 4]),
        (5, "Push / pull / legs", ["push", "pull", "legs", "push", "pull"], [0, 1, 2, 4, 5]),
        (6, "Push / pull / legs", ["push", "pull", "legs"] * 2, [0, 1, 2, 3, 4, 5]),
    ],
)
def test_split_by_days(days, split, kinds, offsets):
    plan = build(days_per_week=days)
    assert plan.split == split
    assert [s.kind for s in plan.sessions] == kinds
    assert [s.day_offset for s in plan.sessions] == offsets


def test_session_groups_follow_split():
    full = build(days_per_week=3, minutes_per_day=40).sessions[0]
    assert {BY_CODE[p.code].group for p in full.exercises} == {"push", "pull", "legs", "core"}
    lower = build(days_per_week=4).sessions[1]
    assert {BY_CODE[p.code].group for p in lower.exercises} <= {"legs", "core"}
    pull_day = build(days_per_week=5).sessions[1]
    assert {BY_CODE[p.code].group for p in pull_day.exercises} <= {"pull", "core"}


def test_no_bar_means_no_bar_exercises_but_still_pulling():
    plan = build(has_pullup_bar=False, days_per_week=5)
    assert not any(e.needs_bar for e in main_exercises(plan))
    assert any(e.group == "pull" for e in main_exercises(plan))


def test_bar_exercises_used_when_available():
    plan = build(has_pullup_bar=True, days_per_week=5, level="advanced")
    assert any(e.needs_bar for e in main_exercises(plan))


@pytest.mark.parametrize(
    ("level", "goal", "low", "high"),
    [
        ("beginner", "stay_fit", 1, 2),
        ("intermediate", "stay_fit", 2, 3),
        ("advanced", "lose_fat", 3, 4),
        ("beginner", "build_muscle", 2, 3),
        ("advanced", "build_muscle", 4, 5),
    ],
)
def test_difficulty_from_level_and_goal(level, goal, low, high):
    plan = build(level=level, goal=goal, minutes_per_day=30)
    assert all(low <= e.difficulty <= high for e in main_exercises(plan))


def test_rep_schemes_by_goal():
    for goal, (sets, rmin, rmax, rest) in eng.REP_SCHEMES.items():
        plan = build(goal=goal)
        reps = [p for s in plan.sessions for p in s.exercises if p.target_reps is not None]
        assert reps
        for p in reps:
            assert (p.sets, p.reps_min, p.reps_max, p.rest_s) == (sets, rmin, rmax, rest)
            assert p.target_reps == rmin


def test_muscle_goal_uses_lower_reps_than_fat_loss():
    muscle = build(goal="build_muscle").sessions[0].exercises[0]
    fat = build(goal="lose_fat").sessions[0].exercises[0]
    assert muscle.reps_max < fat.reps_min


def test_beginner_gets_one_set_fewer():
    p = build(level="beginner", goal="build_muscle").sessions[0].exercises[0]
    assert p.sets == 3


def test_timed_targets_by_level():
    for level, (smin, smax) in eng.TIMED_SCHEMES.items():
        plan = build(level=level, days_per_week=6, minutes_per_day=60)
        timed = [p for s in plan.sessions for p in s.exercises if p.target_seconds is not None]
        assert timed, level
        assert all(
            (p.seconds_min, p.seconds_max, p.target_seconds) == (smin, smax, smin) for p in timed
        )


def test_fat_loss_adds_cardio_finisher_only():
    fat = build(goal="lose_fat")
    assert all(s.finisher and BY_CODE[s.finisher.code].group == "cardio" for s in fat.sessions)
    assert all(s.finisher.sets == 3 and s.finisher.rest_s == 30 for s in fat.sessions)
    assert all(s.finisher is None for s in build(goal="stay_fit").sessions)
    assert all(s.finisher is None for s in build(goal="build_muscle").sessions)
    assert not any(e.group == "cardio" for e in main_exercises(fat))


def test_no_repeats_within_a_session_and_variety_across_sessions():
    plan = build(days_per_week=3, minutes_per_day=60)
    for s in plan.sessions:
        codes = [p.code for p in s.exercises]
        assert len(codes) == len(set(codes))
    assert plan.sessions[0].exercises != plan.sessions[1].exercises


def test_warmup_cooldown_and_estimate():
    s = build(minutes_per_day=20).sessions[0]
    assert len(s.warmup) == 3 and len(s.cooldown) == 3
    assert 10 <= s.est_minutes <= 40


def test_bad_days():
    with pytest.raises(ValueError):
        build(days_per_week=1)


def test_summary():
    L = eng.LoggedSet
    sets = [
        L("pushup", 1, 10, 12, None, None),
        L("pushup", 2, 10, 8, None, None),
        L("forearm_plank", 1, None, None, 30, 30),
        L("table_row", 1, 10, None, None, None),
        L("table_row", 2, 10, None, None, None),
    ]
    s = eng.summarize(sets)
    assert (s.sets_planned, s.sets_done, s.targets_met) == (5, 3, 2)
    assert (s.total_reps, s.total_seconds, s.exercises_skipped) == (20, 30, 1)
    assert s.completion_pct == 60
    assert eng.summarize([]).completion_pct == 0
