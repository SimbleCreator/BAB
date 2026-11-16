from datetime import date, timedelta

import pytest

from app.engines import activity_engine as eng

BODY = eng.BodyStats(height_cm=170, weight_kg=70)


def test_stride_is_height_times_0_415():
    assert eng.stride_m(170) == pytest.approx(0.7055)
    assert eng.stride_m(200) == pytest.approx(0.83)


def test_distance_estimate_from_steps():
    assert eng.estimate_distance_m(10_000, 170) == 7055
    assert eng.estimate_distance_m(0, 170) == 0


def test_calorie_estimate_scales_with_weight():
    assert eng.estimate_active_kcal(10_000, 70) == 400  # 10000 x 0.04 x 1
    assert eng.estimate_active_kcal(10_000, 105) == 600  # x 1.5
    assert eng.estimate_active_kcal(10_000, 35) == 200


def test_resolve_estimates_only_blank_fields():
    v = eng.resolve(eng.ActivityInput(10_000, None, None), BODY)
    assert (v.distance_m, v.distance_estimated) == (7055, True)
    assert (v.active_kcal, v.active_kcal_estimated) == (400, True)

    v = eng.resolve(eng.ActivityInput(10_000, 8000, None), BODY)
    assert (v.distance_m, v.distance_estimated) == (8000, False)
    assert v.active_kcal_estimated is True

    v = eng.resolve(eng.ActivityInput(10_000, 8000, 350), BODY)
    assert not v.distance_estimated and not v.active_kcal_estimated


def test_resolve_without_steps_estimates_nothing():
    v = eng.resolve(eng.ActivityInput(None, None, 300), BODY)
    assert v.distance_m is None and not v.distance_estimated
    assert v.active_kcal == 300 and not v.active_kcal_estimated


def test_goal_met_is_inclusive():
    assert eng.goal_met(8000, 8000)
    assert not eng.goal_met(7999, 8000)
    assert not eng.goal_met(None, 8000)


TODAY = date(2026, 3, 10)


def days_back(*offsets: int) -> list[date]:
    return [TODAY - timedelta(days=o) for o in offsets]


def test_current_streak_counts_back_from_today():
    assert eng.current_streak(days_back(0, 1, 2), TODAY) == 3


def test_current_streak_today_in_progress_does_not_break_it():
    assert eng.current_streak(days_back(1, 2, 3), TODAY) == 3


def test_current_streak_gap_resets():
    assert eng.current_streak(days_back(0, 2, 3), TODAY) == 1
    assert eng.current_streak(days_back(2, 3), TODAY) == 0
    assert eng.current_streak([], TODAY) == 0


def test_longest_streak():
    assert eng.longest_streak(days_back(0, 1, 5, 6, 7, 8, 20)) == 4
    assert eng.longest_streak([]) == 0
    assert eng.longest_streak(days_back(3)) == 1


# Easy days (M14) -----------------------------------------------------------------------


def test_easy_days_left_per_monday_week():
    from datetime import date

    from app.engines import activity_engine as ae

    wed = date(2026, 11, 18)
    assert ae.easy_days_left([], wed) == 2
    assert ae.easy_days_left([date(2026, 11, 16)], wed) == 1
    assert ae.easy_days_left([date(2026, 11, 16), date(2026, 11, 17)], wed) == 0
    # Last week's do not count.
    assert ae.easy_days_left([date(2026, 11, 15), date(2026, 11, 14)], wed) == 2


def test_quiet_streak():
    from datetime import date, timedelta

    from app.engines import activity_engine as ae

    today = date(2026, 11, 18)
    joined = today - timedelta(days=30)
    assert ae.quiet_streak([], today, joined) is True
    assert ae.quiet_streak([today], today, joined) is True  # today does not count
    assert ae.quiet_streak([today - timedelta(days=2)], today, joined) is False
    assert ae.quiet_streak([today - timedelta(days=4)], today, joined) is True
    assert ae.quiet_streak([], today, today - timedelta(days=2)) is False  # new account
    assert ae.quiet_streak([], today, today - timedelta(days=3)) is True
