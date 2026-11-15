"""Daily activity rules: estimates for blank fields and step-goal streaks.

See docs/rules.md, section "Daily activity".
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

STRIDE_FACTOR = 0.415  # stride length = height_cm x 0.415 / 100 metres
KCAL_PER_STEP = 0.04  # at the reference weight
REFERENCE_WEIGHT_KG = 70.0


@dataclass(frozen=True)
class ActivityInput:
    """What the user entered. None means the field was left blank."""

    steps: int | None
    distance_m: int | None
    active_kcal: int | None


@dataclass(frozen=True)
class BodyStats:
    height_cm: float
    weight_kg: float


@dataclass(frozen=True)
class ActivityValues:
    """Values to show. A field is estimated only when the user left it blank."""

    steps: int | None
    distance_m: int | None
    active_kcal: int | None
    distance_estimated: bool
    active_kcal_estimated: bool


def stride_m(height_cm: float) -> float:
    return height_cm * STRIDE_FACTOR / 100


def estimate_distance_m(steps: int, height_cm: float) -> int:
    return round(steps * stride_m(height_cm))


def estimate_active_kcal(steps: int, weight_kg: float) -> int:
    return round(steps * KCAL_PER_STEP * (weight_kg / REFERENCE_WEIGHT_KG))


def resolve(entry: ActivityInput, body: BodyStats) -> ActivityValues:
    distance, distance_est = entry.distance_m, False
    kcal, kcal_est = entry.active_kcal, False
    if entry.steps is not None:
        if distance is None:
            distance, distance_est = estimate_distance_m(entry.steps, body.height_cm), True
        if kcal is None:
            kcal, kcal_est = estimate_active_kcal(entry.steps, body.weight_kg), True
    return ActivityValues(entry.steps, distance, kcal, distance_est, kcal_est)


def goal_met(steps: int | None, step_goal: int) -> bool:
    return steps is not None and steps >= step_goal


def current_streak(goal_days: Iterable[date], today: date) -> int:
    """Consecutive days meeting the step goal, ending today.

    Today is still in progress, so if today is not met yet the streak ending
    yesterday still counts.
    """
    met = set(goal_days)
    day = today if today in met else today - timedelta(days=1)
    streak = 0
    while day in met:
        streak += 1
        day -= timedelta(days=1)
    return streak


def longest_streak(goal_days: Iterable[date]) -> int:
    best = run = 0
    previous: date | None = None
    for day in sorted(set(goal_days)):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day
    return best
