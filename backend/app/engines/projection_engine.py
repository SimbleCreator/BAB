"""How long until the target weight: an honest range, never a promise.

Before there is enough data, the estimate comes from the daily calorie gap (maintenance
minus the calorie target): 7,700 kcal is taken as about 1 kg of body weight, and the
gap is assumed to work at 80-120% of its size, which gives a range of weeks. The speed is
capped at a safe rate (1% of body weight a week for loss, 0.5% for gain). Once there are
TREND_MIN_CHECKINS check-ins over at least TREND_MIN_DAYS days, the user's real weekly
trend (a straight-line fit through recent check-ins) replaces the formula.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from math import ceil
from typing import Literal

KCAL_PER_KG = 7700
EFFECT_LOW, EFFECT_HIGH = 0.8, 1.2
MAX_LOSS_PCT_PER_WEEK = 1.0
MAX_GAIN_PCT_PER_WEEK = 0.5
REACHED_WITHIN_KG = 0.3
TREND_MIN_CHECKINS = 3
TREND_MIN_DAYS = 14
TREND_WINDOW_DAYS = 56
# A trend slower than this (kg a week) toward the target counts as stalled.
TREND_MIN_RATE = 0.05
MAX_WEEKS = 156

Status = Literal["no_target", "reached", "on_track", "stalled", "no_gap"]
Method = Literal["formula", "trend"]


@dataclass(frozen=True)
class WeighIn:
    day: date
    weight_kg: float


@dataclass(frozen=True)
class Projection:
    status: Status
    method: Method | None
    current_kg: float
    target_kg: float | None
    kg_to_go: float | None  # target - current: negative to lose, positive to gain
    weekly_rate_kg: float | None  # signed: negative is loss
    weeks_min: int | None
    weeks_max: int | None
    date_min: date | None
    date_max: date | None
    too_fast: bool  # the real trend is faster than the safe rate


def safe_rate(current_kg: float, losing: bool) -> float:
    """Fastest weekly change (kg, positive) treated as safe."""
    pct = MAX_LOSS_PCT_PER_WEEK if losing else MAX_GAIN_PCT_PER_WEEK
    return current_kg * pct / 100


def trend_rate(weigh_ins: list[WeighIn], today: date) -> float | None:
    """Weekly change from a least-squares line through recent check-ins, or None when there
    are too few (fewer than TREND_MIN_CHECKINS in the window, or spanning under
    TREND_MIN_DAYS days)."""
    start = today - timedelta(days=TREND_WINDOW_DAYS)
    pts = sorted((w for w in weigh_ins if start <= w.day <= today), key=lambda w: w.day)
    if len(pts) < TREND_MIN_CHECKINS or (pts[-1].day - pts[0].day).days < TREND_MIN_DAYS:
        return None
    xs = [(p.day - pts[0].day).days for p in pts]
    ys = [p.weight_kg for p in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    denom = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / denom
    return round(slope * 7, 2)


def _weeks(kg: float, rate: float) -> int:
    return min(MAX_WEEKS, max(1, ceil(kg / rate)))


def project(
    current_kg: float,
    target_kg: float | None,
    daily_gap_kcal: int,
    weigh_ins: list[WeighIn],
    today: date,
) -> Projection:
    """`daily_gap_kcal` is maintenance minus the calorie target: positive is a deficit."""

    def out(status: Status, **kw) -> Projection:
        base = dict(
            method=None,
            kg_to_go=None if target_kg is None else round(target_kg - current_kg, 1),
            weekly_rate_kg=None,
            weeks_min=None,
            weeks_max=None,
            date_min=None,
            date_max=None,
            too_fast=False,
        )
        return Projection(status, current_kg=current_kg, target_kg=target_kg, **(base | kw))

    if target_kg is None:
        return out("no_target")
    to_go = target_kg - current_kg
    if abs(to_go) <= REACHED_WITHIN_KG:
        return out("reached")
    losing = to_go < 0
    cap = safe_rate(current_kg, losing)

    trend = trend_rate(weigh_ins, today)
    if trend is not None:
        toward = -trend if losing else trend
        if toward < TREND_MIN_RATE:
            return out("stalled", method="trend", weekly_rate_kg=trend)
        fast, slow = toward * EFFECT_HIGH, toward * EFFECT_LOW
        too_fast = toward > cap
        method: Method = "trend"
        rate = trend
    else:
        # A deficit moves toward a lower target, a surplus toward a higher one.
        toward = (daily_gap_kcal if losing else -daily_gap_kcal) * 7 / KCAL_PER_KG
        if toward <= 0:
            return out("no_gap", method="formula")
        fast = min(toward * EFFECT_HIGH, cap)
        slow = min(toward * EFFECT_LOW, cap)
        too_fast = False
        method = "formula"
        rate = round(-toward if losing else toward, 2)

    weeks_min, weeks_max = _weeks(abs(to_go), fast), _weeks(abs(to_go), slow)
    return out(
        "on_track",
        method=method,
        weekly_rate_kg=rate,
        weeks_min=weeks_min,
        weeks_max=weeks_max,
        date_min=today + timedelta(weeks=weeks_min),
        date_max=today + timedelta(weeks=weeks_max),
        too_fast=too_fast,
    )
