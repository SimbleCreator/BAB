from datetime import date, timedelta

import pytest

from app.engines import projection_engine as pe

TODAY = date(2026, 11, 16)


def w(days_ago: int, kg: float) -> pe.WeighIn:
    return pe.WeighIn(TODAY - timedelta(days=days_ago), kg)


def test_no_target_and_reached():
    assert pe.project(80, None, 500, [], TODAY).status == "no_target"
    p = pe.project(80, 79.8, 500, [], TODAY)
    assert p.status == "reached" and p.kg_to_go == -0.2
    assert pe.project(80, 79.6, 500, [], TODAY).status == "on_track"


def test_formula_range_from_calorie_gap():
    # 550 kcal a day = 3,850 a week = 0.5 kg a week; 80-120% gives 0.4 to 0.6 kg.
    p = pe.project(80, 75, 550, [], TODAY)
    assert (p.status, p.method) == ("on_track", "formula")
    assert p.weekly_rate_kg == -0.5
    assert (p.weeks_min, p.weeks_max) == (9, 13)  # 5/0.6 = 8.3, 5/0.4 = 12.5
    assert p.date_min == TODAY + timedelta(weeks=9)
    assert p.kg_to_go == -5


def test_formula_capped_at_safe_loss():
    # 2,000 kcal a day would be 1.8 kg a week; capped at 1% of 70 kg = 0.7 kg.
    p = pe.project(70, 63, 2000, [], TODAY)
    assert (p.weeks_min, p.weeks_max) == (10, 10)


def test_formula_gain_capped_at_half_percent():
    # Surplus 1,100 kcal a day = 1 kg a week; capped at 0.5% of 60 kg = 0.3 kg.
    p = pe.project(60, 63, -1100, [], TODAY)
    assert p.status == "on_track" and p.weekly_rate_kg == 1.0
    assert (p.weeks_min, p.weeks_max) == (10, 10)


@pytest.mark.parametrize("gap", [0, -200])
def test_no_gap_when_target_calories_do_not_move_toward_goal(gap):
    assert pe.project(80, 75, gap, [], TODAY).status == "no_gap"
    assert pe.project(60, 65, -gap if gap else 0, [], TODAY).status == "no_gap"


def test_trend_needs_three_checkins_over_fourteen_days():
    assert pe.trend_rate([w(10, 80), w(5, 79.5), w(0, 79)], TODAY) is None  # 10 days
    assert pe.trend_rate([w(14, 80), w(0, 79)], TODAY) is None  # 2 check-ins
    assert pe.trend_rate([w(14, 80), w(7, 79.5), w(0, 79)], TODAY) == -0.5
    # Check-ins older than 8 weeks are ignored.
    old = [w(70, 90), w(14, 80), w(7, 79.5), w(0, 79)]
    assert pe.trend_rate(old, TODAY) == -0.5


def test_trend_replaces_formula():
    pts = [w(14, 80), w(7, 79.5), w(0, 79)]
    p = pe.project(79, 75, 1000, pts, TODAY)
    assert p.method == "trend" and p.weekly_rate_kg == -0.5
    assert (p.weeks_min, p.weeks_max) == (7, 10)  # 4/0.6 = 6.7, 4/0.4 = 10
    assert p.too_fast is False


def test_trend_too_fast_and_stalled():
    fast = [w(14, 84), w(7, 82), w(0, 80)]  # 2 kg a week > 0.8 kg
    assert pe.project(80, 70, 500, fast, TODAY).too_fast is True
    flat = [w(14, 80), w(7, 80.1), w(0, 80)]
    p = pe.project(80, 75, 500, flat, TODAY)
    assert (p.status, p.method) == ("stalled", "trend")
    rising = [w(14, 79), w(7, 79.5), w(0, 80)]
    assert pe.project(80, 75, 500, rising, TODAY).status == "stalled"


def test_weeks_capped():
    p = pe.project(80, 40, 10, [], TODAY)
    assert p.weeks_max == pe.MAX_WEEKS
