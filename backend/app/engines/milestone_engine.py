"""Milestones: definitions, progress and unlock rules.

Each milestone has a target and a progress function over ProgressStats. A milestone
unlocks when progress reaches the target. Unlocks are permanent: callers never
remove them, even if the data that earned them is later deleted.
See docs/rules.md, section "Milestones".
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

Category = Literal["steps", "runs", "training", "food", "checkins", "habits"]
Unit = Literal["steps", "m", "count", "days", "weeks"]


@dataclass(frozen=True)
class ProgressStats:
    """Everything the milestones look at. All values are totals over the user's history."""

    best_day_steps: int = 0
    total_steps: int = 0
    run_count: int = 0
    longest_run_m: int = 0
    total_run_m: int = 0
    longest_step_streak: int = 0
    checkin_count: int = 0
    workout_count: int = 0
    meal_days: int = 0
    habit_weeks_within: int = 0


@dataclass(frozen=True)
class MilestoneDef:
    code: str
    title: str
    description: str
    category: Category
    target: int
    unit: Unit
    value: Callable[[ProgressStats], int]


MILESTONES: tuple[MilestoneDef, ...] = (
    MilestoneDef(
        "steps_5k_day",
        "5K step day",
        "Walk 5,000 steps in one day.",
        "steps",
        5_000,
        "steps",
        lambda s: s.best_day_steps,
    ),
    MilestoneDef(
        "steps_10k_day",
        "10K step day",
        "Walk 10,000 steps in one day.",
        "steps",
        10_000,
        "steps",
        lambda s: s.best_day_steps,
    ),
    MilestoneDef(
        "steps_100k_total",
        "100K club",
        "Reach 100,000 steps in total.",
        "steps",
        100_000,
        "steps",
        lambda s: s.total_steps,
    ),
    MilestoneDef(
        "streak_7",
        "One solid week",
        "Meet your step goal 7 days in a row.",
        "steps",
        7,
        "days",
        lambda s: s.longest_step_streak,
    ),
    MilestoneDef(
        "streak_30",
        "Month of momentum",
        "Meet your step goal 30 days in a row.",
        "steps",
        30,
        "days",
        lambda s: s.longest_step_streak,
    ),
    MilestoneDef(
        "run_first",
        "First run",
        "Log your first run.",
        "runs",
        1,
        "count",
        lambda s: s.run_count,
    ),
    MilestoneDef(
        "run_5k",
        "5 km run",
        "Run 5 km in a single run.",
        "runs",
        5_000,
        "m",
        lambda s: s.longest_run_m,
    ),
    MilestoneDef(
        "run_10k",
        "10 km run",
        "Run 10 km in a single run.",
        "runs",
        10_000,
        "m",
        lambda s: s.longest_run_m,
    ),
    MilestoneDef(
        "run_25k_total",
        "25 km on the clock",
        "Run 25 km in total.",
        "runs",
        25_000,
        "m",
        lambda s: s.total_run_m,
    ),
    MilestoneDef(
        "run_50k_total",
        "50 km on the clock",
        "Run 50 km in total.",
        "runs",
        50_000,
        "m",
        lambda s: s.total_run_m,
    ),
    MilestoneDef(
        "workout_first",
        "First workout",
        "Finish your first planned workout.",
        "training",
        1,
        "count",
        lambda s: s.workout_count,
    ),
    MilestoneDef(
        "workout_10",
        "10 workouts",
        "Finish 10 workouts.",
        "training",
        10,
        "count",
        lambda s: s.workout_count,
    ),
    MilestoneDef(
        "workout_50",
        "50 workouts",
        "Finish 50 workouts.",
        "training",
        50,
        "count",
        lambda s: s.workout_count,
    ),
    MilestoneDef(
        "meals_7_days",
        "A week of meals",
        "Log meals on 7 different days.",
        "food",
        7,
        "days",
        lambda s: s.meal_days,
    ),
    MilestoneDef(
        "checkins_4",
        "Four check-ins",
        "Complete 4 weekly check-ins.",
        "checkins",
        4,
        "count",
        lambda s: s.checkin_count,
    ),
    MilestoneDef(
        "checkins_12",
        "Twelve check-ins",
        "Complete 12 weekly check-ins.",
        "checkins",
        12,
        "count",
        lambda s: s.checkin_count,
    ),
    MilestoneDef(
        "habit_week_within",
        "Week within plan",
        "Finish a full week inside your reduction plan's allowance.",
        "habits",
        1,
        "weeks",
        lambda s: s.habit_weeks_within,
    ),
)

BY_CODE = {m.code: m for m in MILESTONES}


def current_value(milestone: MilestoneDef, stats: ProgressStats) -> int:
    return max(0, milestone.value(stats))


def is_met(milestone: MilestoneDef, stats: ProgressStats) -> bool:
    return current_value(milestone, stats) >= milestone.target


def newly_unlocked(stats: ProgressStats, already: Iterable[str]) -> list[str]:
    """Codes that are met now and were not unlocked before, in definition order."""
    done = set(already)
    return [m.code for m in MILESTONES if m.code not in done and is_met(m, stats)]
