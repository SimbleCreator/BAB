from datetime import datetime, timedelta, timezone

import pytest

from app.engines import run_engine as eng
from tests.gpx_helpers import M_PER_DEG_LAT, track


def pts(n, m_step, s_step, segment=0):
    return [eng.TrackPoint(lat, lng, None, t, segment) for lat, lng, t in track(n, m_step, s_step)]


def test_haversine_one_degree_of_latitude():
    a, b = eng.TrackPoint(0, 0), eng.TrackPoint(1, 0)
    assert eng.haversine_m(a, b) == pytest.approx(M_PER_DEG_LAT, rel=1e-9)


def test_distance_not_counted_across_segments():
    first = pts(11, 100, 30, segment=1)  # 1000 m
    t = first[-1].time + timedelta(minutes=5)
    gap = eng.TrackPoint(first[-1].lat + 0.01, first[-1].lng, None, t, segment=2)  # ~1.1 km jump
    after = eng.TrackPoint(
        gap.lat + 100 / M_PER_DEG_LAT, gap.lng, None, t + timedelta(seconds=30), 2
    )
    stats = eng.track_stats([*first, gap, after])
    assert stats.distance_m == 1100


def test_track_stats():
    stats = eng.track_stats(pts(51, 100, 30))  # 5 km in 25 min
    assert stats.distance_m == 5000
    assert stats.duration_s == 1500
    assert stats.started_at == datetime(2026, 3, 1, 1, 0, tzinfo=timezone.utc)


def test_track_stats_needs_times():
    with pytest.raises(ValueError):
        eng.track_stats([eng.TrackPoint(0, 0), eng.TrackPoint(1, 0)])


def test_pace():
    assert eng.pace_s_per_km(5000, 1500) == 300
    assert eng.pace_s_per_km(0, 100) is None
    assert eng.pace_s_per_km(1000, 0) is None


def test_splits_even_pace_with_partial_last_km():
    s = eng.splits(pts(26, 100, 30))  # 2.5 km at 5:00 /km
    assert [(x.km, x.distance_m, x.duration_s, x.pace_s_per_km) for x in s] == [
        (1, 1000, 300, 300),
        (2, 1000, 300, 300),
        (3, 500, 150, 300),
    ]


def test_split_boundary_interpolated_inside_a_segment():
    # 300 m steps: the 1 km mark falls a third of the way through the 4th step.
    s = eng.splits(pts(5, 300, 60))  # 1200 m in 240 s
    assert s[0].distance_m == 1000
    assert s[0].duration_s == 200
    assert (s[1].distance_m, s[1].duration_s) == (200, 40)


def test_splits_scaled_to_stored_distance():
    s = eng.splits(pts(21, 100, 30), total_distance_m=4000)  # 2 km track shown as 4 km
    assert [x.distance_m for x in s] == [1000, 1000, 1000, 1000]
    assert sum(x.duration_s for x in s) == 600


def test_tiny_gps_tail_is_ignored():
    base = pts(11, 100, 30)  # exactly 1 km
    last = base[-1]
    tail = eng.TrackPoint(
        last.lat + 5 / M_PER_DEG_LAT, last.lng, None, last.time + timedelta(seconds=2)
    )
    assert len(eng.splits([*base, tail])) == 1
    far = eng.TrackPoint(
        last.lat + 50 / M_PER_DEG_LAT, last.lng, None, last.time + timedelta(seconds=15)
    )
    assert len(eng.splits([*base, far])) == 2


def test_downsample():
    many = pts(5000, 1, 1)
    out = eng.downsample(many, 2000)
    assert len(out) == 2000
    assert out[0] == many[0] and out[-1] == many[-1]
    few = pts(10, 1, 1)
    assert eng.downsample(few, 2000) == few


def test_calories_formula():
    assert eng.calories_kcal(70, 10_000) == 725  # 70 x 10 x 1.036 = 725.2
    assert eng.calories_kcal(64.5, 5000) == 334  # 334.11
