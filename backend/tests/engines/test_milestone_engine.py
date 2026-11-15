import pytest

from app.engines import milestone_engine as eng
from app.engines.milestone_engine import ProgressStats as S

# (code, stats just below target, stats at target)
THRESHOLDS = [
    ("steps_5k_day", S(best_day_steps=4_999), S(best_day_steps=5_000)),
    ("steps_10k_day", S(best_day_steps=9_999), S(best_day_steps=10_000)),
    ("steps_100k_total", S(total_steps=99_999), S(total_steps=100_000)),
    ("streak_7", S(longest_step_streak=6), S(longest_step_streak=7)),
    ("streak_30", S(longest_step_streak=29), S(longest_step_streak=30)),
    ("run_first", S(run_count=0), S(run_count=1)),
    ("run_5k", S(longest_run_m=4_999), S(longest_run_m=5_000)),
    ("run_10k", S(longest_run_m=9_999), S(longest_run_m=10_000)),
    ("run_25k_total", S(total_run_m=24_999), S(total_run_m=25_000)),
    ("run_50k_total", S(total_run_m=49_999), S(total_run_m=50_000)),
    ("workout_first", S(workout_count=0), S(workout_count=1)),
    ("workout_10", S(workout_count=9), S(workout_count=10)),
    ("workout_50", S(workout_count=49), S(workout_count=50)),
    ("meals_7_days", S(meal_days=6), S(meal_days=7)),
    ("checkins_4", S(checkin_count=3), S(checkin_count=4)),
    ("checkins_12", S(checkin_count=11), S(checkin_count=12)),
    ("habit_week_within", S(habit_weeks_within=0), S(habit_weeks_within=1)),
]


def test_every_milestone_has_a_threshold_test():
    assert {c for c, _, _ in THRESHOLDS} == {m.code for m in eng.MILESTONES}


@pytest.mark.parametrize(("code", "below", "at"), THRESHOLDS)
def test_threshold(code, below, at):
    m = eng.BY_CODE[code]
    assert not eng.is_met(m, below)
    assert eng.is_met(m, at)


def test_codes_unique_and_short():
    codes = [m.code for m in eng.MILESTONES]
    assert len(codes) == len(set(codes))
    assert all(len(c) <= 40 for c in codes)


def test_newly_unlocked_skips_already_unlocked():
    stats = S(best_day_steps=12_000, run_count=1)
    assert eng.newly_unlocked(stats, []) == ["steps_5k_day", "steps_10k_day", "run_first"]
    assert eng.newly_unlocked(stats, ["steps_5k_day", "run_first"]) == ["steps_10k_day"]
    assert eng.newly_unlocked(S(), []) == []
