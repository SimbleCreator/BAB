"""Weekly adjustment after a check-in: calories by weight trend, training by last week.

Pure rules; see docs/rules.md, section "Weekly adjustment".
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Literal

from app.engines.training_engine import (
    Exercise,
    Prescription,
    SessionPlan,
    TrainingInput,
    prescribe,
)

# Nutrition --------------------------------------------------------------------

LOSE_FAT_SLOW_PCT = 0.25  # losing less than this per week -> eat 100 less
LOSE_FAT_FAST_PCT = 1.0  # losing more than this per week -> eat 150 more
MUSCLE_SLOW_PCT = 0.1  # gaining less than this per week -> eat 100 more
MUSCLE_FAST_PCT = 0.5  # gaining more than this per week -> eat 100 less
STAY_FIT_BAND_PCT = 0.5  # changing more than this either way -> 100 toward stable


@dataclass(frozen=True)
class NutritionDecision:
    weekly_change_pct: float  # + gain, - loss, as % of the earlier weight
    requested_kcal: int  # what the rule asks for
    new_kcal: int  # after the calorie floor
    floor_applied: bool
    reason: str


def weekly_change_pct(previous_kg: float, latest_kg: float, days_between: int) -> float:
    """Weight change scaled to 7 days, as a percentage of the earlier weight."""
    if days_between <= 0 or previous_kg <= 0:
        raise ValueError("need two check-ins on different days")
    return (latest_kg - previous_kg) * 7 / days_between / previous_kg * 100


def _fmt(pct: float) -> str:
    return f"{abs(pct):.2f}%"


def nutrition_decision(goal: str, pct: float, current_kcal: int, floor: int) -> NutritionDecision:
    direction = "gained" if pct > 0 else "lost" if pct < 0 else "kept"
    trend = (
        f"You {direction} {_fmt(pct)} of your body weight per week"
        if pct
        else ("Your weight held steady")
    )
    delta = 0
    if goal == "lose_fat":
        loss = -pct
        if loss < LOSE_FAT_SLOW_PCT:
            delta, why = -100, f"slower than the {LOSE_FAT_SLOW_PCT}% aim, so 100 kcal less a day"
        elif loss > LOSE_FAT_FAST_PCT:
            delta, why = (
                150,
                f"faster than {LOSE_FAT_FAST_PCT}%, so 150 kcal more a day to protect muscle",
            )
        else:
            why = "right on track, so calories stay the same"
    elif goal == "build_muscle":
        if pct < MUSCLE_SLOW_PCT:
            delta, why = 100, f"under the {MUSCLE_SLOW_PCT}% aim, so 100 kcal more a day"
        elif pct > MUSCLE_FAST_PCT:
            delta, why = -100, f"over {MUSCLE_FAST_PCT}%, so 100 kcal less a day to limit fat gain"
        else:
            why = "right on track, so calories stay the same"
    else:
        if pct > STAY_FIT_BAND_PCT:
            delta, why = -100, "more than you want when staying fit, so 100 kcal less a day"
        elif pct < -STAY_FIT_BAND_PCT:
            delta, why = 100, "more than you want when staying fit, so 100 kcal more a day"
        else:
            why = "steady, so calories stay the same"

    requested = current_kcal + delta
    new = max(requested, floor)
    reason = f"{trend}: {why}."
    if new != requested:
        reason += f" Kept at the {floor} kcal minimum."
    return NutritionDecision(round(pct, 2), requested, new, new != requested, reason)


# Training ---------------------------------------------------------------------

PROGRESS_AT = 0.8  # share of planned sessions done to progress
REDUCE_BELOW = 0.5  # share below which sets are reduced
REP_STEP = 2
SECONDS_STEP = 5
MIN_SETS = 1

TrainingDecision = Literal["progress", "reduce", "unchanged", "no_data"]


@dataclass(frozen=True)
class LastWeek:
    planned_sessions: int
    done_sessions: int
    # exercise code -> every logged set met its target (only exercises with logged sets)
    targets_met: Mapping[str, bool]

    @property
    def completion(self) -> float:
        return self.done_sessions / self.planned_sessions if self.planned_sessions else 0.0


def training_decision(week: LastWeek) -> TrainingDecision:
    if week.planned_sessions == 0:
        return "no_data"
    if week.completion >= PROGRESS_AT:
        return "progress"
    if week.completion < REDUCE_BELOW:
        return "reduce"
    return "unchanged"


@dataclass(frozen=True)
class TrainingResult:
    decision: TrainingDecision
    sessions: tuple[SessionPlan, ...]
    changes: tuple[str, ...]


def _progress_one(
    p: Prescription,
    library: Mapping[str, Exercise],
    inp: TrainingInput,
    taken: set[str],
) -> tuple[Prescription, str | None]:
    ex = library.get(p.code)
    name = ex.name if ex else p.code
    if p.target_reps is not None and p.reps_max is not None and p.target_reps < p.reps_max:
        new = min(p.reps_max, p.target_reps + REP_STEP)
        return replace(p, target_reps=new), f"{name}: {p.target_reps} to {new} reps"
    if (
        p.target_seconds is not None
        and p.seconds_max is not None
        and p.target_seconds < p.seconds_max
    ):
        new = min(p.seconds_max, p.target_seconds + SECONDS_STEP)
        return replace(p, target_seconds=new), f"{name}: {p.target_seconds} to {new} s"
    # At the top of the range: move to the harder variation if there is a usable one.
    harder = library.get(ex.harder) if ex and ex.harder else None
    if harder is None or (harder.needs_bar and not inp.has_pullup_bar) or harder.code in taken:
        return p, None
    nxt = replace(prescribe(harder, inp), sets=p.sets)
    return nxt, f"{name} to {harder.name}"


def apply_training(
    sessions: Sequence[SessionPlan],
    week: LastWeek,
    library: Mapping[str, Exercise],
    inp: TrainingInput,
) -> TrainingResult:
    decision = training_decision(week)
    changes: dict[str, str] = {}
    out: list[SessionPlan] = []
    if decision == "progress":
        met = {code for code, ok in week.targets_met.items() if ok}
        for s in sessions:
            taken = {p.code for p in s.exercises}
            new_ex = []
            for p in s.exercises:
                if p.code in met:
                    q, note = _progress_one(p, library, inp, taken)
                    if note:
                        changes.setdefault(p.code, note)
                        taken.discard(p.code)
                        taken.add(q.code)
                    new_ex.append(q)
                else:
                    new_ex.append(p)
            out.append(replace(s, exercises=tuple(new_ex)))
    elif decision == "reduce":
        for s in sessions:
            new_ex = tuple(replace(p, sets=max(MIN_SETS, p.sets - 1)) for p in s.exercises)
            out.append(replace(s, exercises=new_ex))
        if any(p.sets > MIN_SETS for s in sessions for p in s.exercises):
            changes["_all"] = "One set fewer for each exercise"
    else:
        out = list(sessions)
    return TrainingResult(decision, tuple(out), tuple(changes.values()))


def training_summary(week: LastWeek, result: TrainingResult) -> str:
    if result.decision == "no_data":
        return "No planned workouts last week, so training stays the same."
    done = f"You did {week.done_sessions} of {week.planned_sessions} planned workouts"
    pct = round(week.completion * 100)
    if result.decision == "progress":
        if result.changes:
            return f"{done} ({pct}%). Exercises where you hit every target step up."
        return f"{done} ({pct}%). Hit every target on an exercise to step it up next time."
    if result.decision == "reduce":
        return f"{done} ({pct}%). One set fewer per exercise to make the week easier to finish."
    return f"{done} ({pct}%). Training stays the same; 80% or more unlocks progress."
