"""Run rules: track distance, splits, downsampling and calorie estimate.

See docs/rules.md, section "Runs".
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

EARTH_RADIUS_M = 6_371_000.0
KCAL_FACTOR = 1.036  # calories = weight_kg x distance_km x 1.036
MAX_STORED_POINTS = 2000


@dataclass(frozen=True)
class TrackPoint:
    lat: float
    lng: float
    ele_m: float | None = None
    time: datetime | None = None
    segment: int = 0  # distance is not counted across segment breaks


@dataclass(frozen=True)
class Split:
    km: int  # 1-based
    distance_m: int  # 1000 except possibly the last one
    duration_s: int
    pace_s_per_km: int


@dataclass(frozen=True)
class TrackStats:
    distance_m: int
    duration_s: int
    started_at: datetime


def haversine_m(a: TrackPoint, b: TrackPoint) -> float:
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp = p2 - p1
    dl = math.radians(b.lng - a.lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def cumulative_distances(points: Sequence[TrackPoint]) -> list[float]:
    out = [0.0]
    for prev, cur in zip(points, points[1:], strict=False):
        step = haversine_m(prev, cur) if prev.segment == cur.segment else 0.0
        out.append(out[-1] + step)
    return out


def track_stats(points: Sequence[TrackPoint]) -> TrackStats:
    """Distance along the track and elapsed time from first to last timestamp."""
    timed = [p for p in points if p.time is not None]
    if len(points) < 2 or len(timed) < 2:
        raise ValueError("track needs at least two timed points")
    distance = cumulative_distances(points)[-1]
    start, end = timed[0].time, timed[-1].time
    assert start is not None and end is not None  # noqa: S101 - filtered above
    return TrackStats(
        distance_m=round(distance),
        duration_s=max(0, round((end - start).total_seconds())),
        started_at=start,
    )


def pace_s_per_km(distance_m: float, duration_s: float) -> int | None:
    if distance_m <= 0 or duration_s <= 0:
        return None
    return round(duration_s / (distance_m / 1000))


def splits(points: Sequence[TrackPoint], total_distance_m: float | None = None) -> list[Split]:
    """Per-km splits. Time at each km boundary is interpolated between points.

    If total_distance_m is given (the run's stored distance), the track's distances are
    scaled to it so splits always add up to the distance shown to the user.
    """
    timed = [p for p in points if p.time is not None]
    if len(timed) < 2:
        return []
    cum = cumulative_distances(timed)
    if cum[-1] <= 0:
        return []
    if total_distance_m:
        factor = total_distance_m / cum[-1]
        cum = [c * factor for c in cum]
    t0 = timed[0].time
    assert t0 is not None  # noqa: S101
    secs = [(p.time - t0).total_seconds() for p in timed if p.time is not None]

    result: list[Split] = []
    boundary = 1000.0
    last_d, last_t = 0.0, 0.0
    for i in range(1, len(cum)):
        while cum[i] >= boundary:
            span = cum[i] - cum[i - 1]
            frac = (boundary - cum[i - 1]) / span if span > 0 else 0
            t = secs[i - 1] + frac * (secs[i] - secs[i - 1])
            dur = t - last_t
            result.append(Split(len(result) + 1, 1000, round(dur), round(dur)))
            last_d, last_t = boundary, t
            boundary += 1000
    rest_d, rest_t = cum[-1] - last_d, secs[-1] - last_t
    if rest_d >= 10:  # ignore a few metres of GPS tail
        result.append(
            Split(
                len(result) + 1,
                round(rest_d),
                round(rest_t),
                pace_s_per_km(rest_d, rest_t) or 0,
            )
        )
    return result


def downsample(points: Sequence[TrackPoint], limit: int = MAX_STORED_POINTS) -> list[TrackPoint]:
    """Keep at most `limit` evenly spaced points, always including first and last."""
    n = len(points)
    if n <= limit:
        return list(points)
    if limit < 2:
        raise ValueError("limit must be at least 2")
    step = (n - 1) / (limit - 1)
    return [points[round(i * step)] for i in range(limit)]


def calories_kcal(weight_kg: float, distance_m: float) -> int:
    return round(weight_kg * (distance_m / 1000) * KCAL_FACTOR)
