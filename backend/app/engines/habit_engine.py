"""Reduction plan for smoking or drinking.

The allowance shrinks week by week from the user's baseline. A week that ends over its
allowance repeats the same allowance; a week within it moves to the next step. Daily
goals (steps, workout, meals) each unlock a third of the allowance.
See docs/rules.md, section "Habit reduction". This is a reduction plan, not a reward
system: wording elsewhere never presents use as a prize or treat.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

HabitType = Literal["smoking", "drinking"]
Period = Literal["day", "week"]
PACES = (5, 10)  # % of baseline per week: gentle, standard
PERIOD_FOR: dict[str, Period] = {"smoking": "day", "drinking": "week"}
FIRST_STEP = 1  # the first week already reduces by one step
GOALS = 3
DOCTOR_LINE = "A doctor can help if you want to quit completely; ask about support and treatment."


def round_half_up(x: float) -> int:
    return math.floor(x + 0.5)


def allowance(baseline: int, pace_pct: int, step: int) -> int:
    """Units per period at this step: max(0, round(baseline x (1 - pace x step)))."""
    return max(0, round_half_up(baseline * (1 - pace_pct / 100 * step)))


def week_total_allowance(per_period: int, period: Period) -> int:
    return per_period * 7 if period == "day" else per_period


def baseline_week_total(baseline: int, period: Period) -> int:
    return week_total_allowance(baseline, period)


def week_index(started_on: date, day: date) -> int:
    return (day - started_on).days // 7


def week_bounds(started_on: date, index: int) -> tuple[date, date]:
    start = started_on + timedelta(days=7 * index)
    return start, start + timedelta(days=6)


@dataclass(frozen=True)
class WeekResult:
    index: int
    step: int
    allowance_per_period: int
    allowance_total: int
    used: int
    within: bool
    avoided: int  # units below the baseline for the week (0 when over)


def weeks(
    baseline: int, pace_pct: int, period: Period, completed_totals: Sequence[int]
) -> tuple[list[WeekResult], int]:
    """Results for completed weeks, and the step for the week after them.

    A week within its allowance moves to the next step; a week over repeats the step.
    """
    step = FIRST_STEP
    out: list[WeekResult] = []
    base_total = baseline_week_total(baseline, period)
    for i, used in enumerate(completed_totals):
        per = allowance(baseline, pace_pct, step)
        total = week_total_allowance(per, period)
        within = used <= total
        out.append(
            WeekResult(
                i, step, per, total, used, within, max(0, base_total - used) if within else 0
            )
        )
        if within:
            step += 1
    return out, step


@dataclass(frozen=True)
class DayGoals:
    steps: bool
    workout: bool  # planned workout done, or a rest day
    meals: bool

    @property
    def met(self) -> int:
        return int(self.steps) + int(self.workout) + int(self.meals)


@dataclass(frozen=True)
class Availability:
    allowance: int  # for the period (today, or this week)
    unlocked: int
    used: int

    @property
    def available_now(self) -> int:
        return max(0, self.unlocked - self.used)

    @property
    def locked(self) -> int:
        return max(0, self.allowance - self.unlocked)

    @property
    def over(self) -> int:
        return max(0, self.used - self.allowance)


def daily_availability(per_day: int, goals_today: DayGoals, used_today: int) -> Availability:
    """Smoking: each goal met today unlocks a third of today's allowance."""
    unlocked = math.floor(per_day * goals_today.met / GOALS)
    return Availability(per_day, unlocked, used_today)


def weekly_availability(
    per_week: int, goals_by_day: Sequence[DayGoals], used_this_week: int
) -> Availability:
    """Drinking: every goal met on any day of the week unlocks 1/21 of the week's allowance."""
    thirds = sum(g.met for g in goals_by_day)
    unlocked = math.floor(per_week * min(thirds, GOALS * 7) / (GOALS * 7))
    return Availability(per_week, unlocked, used_this_week)
