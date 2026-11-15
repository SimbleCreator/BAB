from datetime import date

import pytest

from app.engines import habit_engine as eng


@pytest.mark.parametrize(
    ("baseline", "pace", "step", "expected"),
    [
        (20, 10, 0, 20),
        (20, 10, 1, 18),
        (20, 10, 5, 10),
        (20, 10, 10, 0),
        (20, 10, 12, 0),  # never below zero
        (10, 5, 1, 10),  # 9.5 rounds half up
        (10, 5, 3, 9),  # 8.5 -> 9
        (14, 5, 2, 13),  # 12.6
        (7, 10, 3, 5),  # 4.9
    ],
)
def test_allowance_formula(baseline, pace, step, expected):
    assert eng.allowance(baseline, pace, step) == expected


def test_week_totals_by_period():
    assert eng.week_total_allowance(10, "day") == 70
    assert eng.week_total_allowance(10, "week") == 10


def test_week_index_and_bounds():
    start = date(2026, 3, 4)
    assert eng.week_index(start, date(2026, 3, 4)) == 0
    assert eng.week_index(start, date(2026, 3, 10)) == 0
    assert eng.week_index(start, date(2026, 3, 11)) == 1
    assert eng.week_bounds(start, 1) == (date(2026, 3, 11), date(2026, 3, 17))


def test_within_moves_on_over_repeats():
    # smoking, baseline 20/day, 10%: step 1 -> 18/day (126/week)
    results, nxt = eng.weeks(20, 10, "day", [126, 130, 110])
    assert [r.step for r in results] == [1, 2, 2]
    assert [r.allowance_per_period for r in results] == [18, 16, 16]
    assert [r.within for r in results] == [True, False, True]
    assert results[0].avoided == 140 - 126
    assert results[1].avoided == 0
    assert nxt == 3


def test_first_week_step_and_drinking_period():
    results, nxt = eng.weeks(10, 10, "week", [])
    assert results == [] and nxt == eng.FIRST_STEP
    results, nxt = eng.weeks(10, 10, "week", [9])
    assert results[0].allowance_total == 9 and results[0].within and results[0].avoided == 1


G = eng.DayGoals


def test_each_goal_unlocks_a_third_of_the_day():
    assert eng.daily_availability(9, G(False, False, False), 0).unlocked == 0
    assert eng.daily_availability(9, G(True, False, False), 0).unlocked == 3
    assert eng.daily_availability(9, G(True, True, False), 0).unlocked == 6
    a = eng.daily_availability(9, G(True, True, True), 2)
    assert (a.unlocked, a.available_now, a.locked, a.over) == (9, 7, 0, 0)
    b = eng.daily_availability(10, G(True, False, False), 5)
    assert (b.unlocked, b.available_now, b.locked, b.over) == (3, 0, 7, 0)
    assert eng.daily_availability(4, G(True, True, True), 6).over == 2


def test_weekly_unlocks_by_goals_across_the_week():
    full_day = G(True, True, True)
    a = eng.weekly_availability(14, [full_day] * 7, 3)
    assert (a.unlocked, a.available_now) == (14, 11)
    b = eng.weekly_availability(14, [full_day, G(True, False, False)], 0)
    assert b.unlocked == 2  # 4 thirds of 21 -> 14 x 4/21 = 2.67 -> 2
    assert b.locked == 12


def test_doctor_line_present():
    assert "doctor" in eng.DOCTOR_LINE.lower()
