"""Rule-based weekly training plan and workout summary.

Inputs are plain dataclasses; no database, web or clock access.
See docs/rules.md, section "Training plan".
"""

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

Group = Literal["push", "pull", "legs", "core", "cardio"]
ExerciseType = Literal["reps", "timed"]

# Training days in the week, as offsets from Monday.
DAY_OFFSETS: dict[int, tuple[int, ...]] = {
    2: (0, 3),
    3: (0, 2, 4),
    4: (0, 1, 3, 4),
    5: (0, 1, 2, 4, 5),
    6: (0, 1, 2, 3, 4, 5),
}

# Slot cycles per session type: groups are taken in this order until the session is full.
TEMPLATES: dict[str, tuple[str, tuple[Group, ...]]] = {
    "full": ("Full body", ("push", "pull", "legs", "core")),
    "upper": ("Upper body", ("push", "pull", "push", "pull", "core")),
    "lower": ("Lower body", ("legs", "legs", "core", "legs", "core")),
    "push": ("Push", ("push", "push", "core", "push")),
    "pull": ("Pull", ("pull", "pull", "core", "pull")),
    "legs": ("Legs", ("legs", "legs", "core", "legs")),
}

SPLITS: dict[int, tuple[str, tuple[str, ...]]] = {
    2: ("Full body", ("full", "full")),
    3: ("Full body", ("full", "full", "full")),
    4: ("Upper / lower", ("upper", "lower", "upper", "lower")),
    5: ("Push / pull / legs", ("push", "pull", "legs", "push", "pull")),
    6: ("Push / pull / legs", ("push", "pull", "legs", "push", "pull", "legs")),
}

LEVEL_DIFFICULTY = {"beginner": 2, "intermediate": 3, "advanced": 4}

# goal -> (sets, reps_min, reps_max, rest seconds)
REP_SCHEMES = {
    "lose_fat": (3, 12, 15, 45),
    "stay_fit": (3, 10, 12, 60),
    "build_muscle": (4, 6, 10, 90),
}
# level -> (seconds_min, seconds_max) for timed exercises
TIMED_SCHEMES = {"beginner": (20, 40), "intermediate": (30, 50), "advanced": (40, 60)}
FINISHER = {"sets": 3, "rest_s": 30}
SECONDS_PER_REP = 3
WARMUP_COUNT = 3
COOLDOWN_COUNT = 3


@dataclass(frozen=True)
class Exercise:
    code: str
    name: str
    group: Group
    difficulty: int
    type: ExerciseType
    needs_bar: bool
    easier: str | None
    harder: str | None
    instructions: str


@dataclass(frozen=True)
class Drill:
    code: str
    name: str
    seconds: int
    instructions: str


@dataclass(frozen=True)
class TrainingInput:
    goal: str  # lose_fat | build_muscle | stay_fit
    level: str  # beginner | intermediate | advanced
    minutes_per_day: int
    days_per_week: int
    has_pullup_bar: bool


@dataclass(frozen=True)
class Prescription:
    code: str
    sets: int
    rest_s: int
    reps_min: int | None = None
    reps_max: int | None = None
    target_reps: int | None = None
    seconds_min: int | None = None
    seconds_max: int | None = None
    target_seconds: int | None = None

    @property
    def work_seconds_per_set(self) -> int:
        if self.target_seconds is not None:
            return self.target_seconds
        return (self.target_reps or 0) * SECONDS_PER_REP


@dataclass(frozen=True)
class SessionPlan:
    day_offset: int  # 0 = Monday
    kind: str
    title: str
    focus: tuple[Group, ...]
    warmup: tuple[str, ...]
    exercises: tuple[Prescription, ...]
    finisher: Prescription | None
    cooldown: tuple[str, ...]
    est_minutes: int

    @property
    def all_prescriptions(self) -> tuple[Prescription, ...]:
        return self.exercises + ((self.finisher,) if self.finisher else ())


@dataclass(frozen=True)
class WeekPlan:
    split: str
    sessions: tuple[SessionPlan, ...]


def exercise_count(minutes_per_day: int) -> int:
    """About 4 exercises for 20 minutes, 6 for 40, 8 for 60; never fewer than 4 or more than 8."""
    return min(8, max(4, math.floor(minutes_per_day / 10 + 0.5) + 2))


def target_difficulty(level: str, goal: str) -> int:
    base = LEVEL_DIFFICULTY[level]
    return min(5, base + 1) if goal == "build_muscle" else base


def prescribe(ex: Exercise, inp: TrainingInput) -> Prescription:
    sets, rmin, rmax, rest = REP_SCHEMES[inp.goal]
    if inp.level == "beginner":
        sets = max(2, sets - 1)
    if ex.type == "timed":
        smin, smax = TIMED_SCHEMES[inp.level]
        return Prescription(
            ex.code, sets, rest, seconds_min=smin, seconds_max=smax, target_seconds=smin
        )
    return Prescription(ex.code, sets, rest, reps_min=rmin, reps_max=rmax, target_reps=rmin)


def finisher_prescription(ex: Exercise, inp: TrainingInput) -> Prescription:
    sets, rest = FINISHER["sets"], FINISHER["rest_s"]
    if ex.type == "timed":
        smin, smax = TIMED_SCHEMES[inp.level]
        return Prescription(
            ex.code, sets, rest, seconds_min=smin, seconds_max=smax, target_seconds=smin
        )
    return Prescription(ex.code, sets, rest, reps_min=8, reps_max=15, target_reps=8)


def pool(library: Sequence[Exercise], group: str, has_bar: bool, target: int) -> list[Exercise]:
    """Exercises for a group, nearest to the target difficulty first.

    Preferred window is target-1..target; exercises outside it follow, nearest first,
    so a group is never empty.
    """
    usable = [e for e in library if e.group == group and (has_bar or not e.needs_bar)]

    def rank(e: Exercise) -> tuple[int, int, str]:
        in_window = target - 1 <= e.difficulty <= target
        return (0 if in_window else 1, abs(e.difficulty - target), e.code)

    return sorted(usable, key=rank)


def _window_size(candidates: list[Exercise], target: int) -> int:
    return sum(1 for e in candidates if target - 1 <= e.difficulty <= target) or len(candidates)


def pick(candidates: list[Exercise], k: int, offset: int, target: int) -> list[Exercise]:
    """k distinct exercises, rotating through the preferred window by offset for variety."""
    if not candidates:
        return []
    window = candidates[: _window_size(candidates, target)]
    rest = candidates[len(window) :]
    rotated = window[offset % len(window) :] + window[: offset % len(window)]
    return (rotated + rest)[:k]


def _drills(drills: Sequence[Drill], count: int, offset: int) -> tuple[str, ...]:
    if not drills:
        return ()
    return tuple(drills[(offset + i) % len(drills)].code for i in range(min(count, len(drills))))


def estimate_minutes(session_items: Sequence[Prescription], warmup_s: int, cooldown_s: int) -> int:
    work = sum(p.sets * (p.work_seconds_per_set + p.rest_s) for p in session_items)
    return max(1, round((work + warmup_s + cooldown_s) / 60))


def build_week(
    inp: TrainingInput,
    library: Sequence[Exercise],
    warmups: Sequence[Drill] = (),
    cooldowns: Sequence[Drill] = (),
) -> WeekPlan:
    if inp.days_per_week not in SPLITS:
        raise ValueError("days_per_week must be 2 to 6")
    split_name, kinds = SPLITS[inp.days_per_week]
    target = target_difficulty(inp.level, inp.goal)
    n = exercise_count(inp.minutes_per_day)
    by_code_drill = {d.code: d for d in (*warmups, *cooldowns)}
    seen: Counter[str] = Counter()
    sessions: list[SessionPlan] = []

    for index, (kind, offset_day) in enumerate(
        zip(kinds, DAY_OFFSETS[inp.days_per_week], strict=True)
    ):
        title, cycle = TEMPLATES[kind]
        occurrence = seen[kind]
        seen[kind] += 1
        slots = [cycle[i % len(cycle)] for i in range(n)]
        per_group = Counter(slots)
        chosen: dict[str, list[Exercise]] = {
            g: pick(pool(library, g, inp.has_pullup_bar, target), k, occurrence * k, target)
            for g, k in per_group.items()
        }
        used: Counter[str] = Counter()
        exercises: list[Prescription] = []
        for g in slots:
            options = chosen[g]
            if used[g] < len(options):
                exercises.append(prescribe(options[used[g]], inp))
            used[g] += 1

        finisher = None
        if inp.goal == "lose_fat":
            cardio = pick(pool(library, "cardio", inp.has_pullup_bar, target), 1, index, target)
            if cardio:
                finisher = finisher_prescription(cardio[0], inp)

        warm = _drills(warmups, WARMUP_COUNT, index)
        cool = _drills(cooldowns, COOLDOWN_COUNT, index)
        items = exercises + ([finisher] if finisher else [])
        est = estimate_minutes(
            items,
            sum(by_code_drill[c].seconds for c in warm),
            sum(by_code_drill[c].seconds for c in cool),
        )
        focus = tuple(dict.fromkeys(slots))
        sessions.append(
            SessionPlan(offset_day, kind, title, focus, warm, tuple(exercises), finisher, cool, est)
        )
    return WeekPlan(split_name, tuple(sessions))


# Workout summary -------------------------------------------------------------


@dataclass(frozen=True)
class LoggedSet:
    exercise_code: str
    set_no: int
    target_reps: int | None
    actual_reps: int | None
    target_seconds: int | None
    actual_seconds: int | None

    @property
    def done(self) -> bool:
        return self.actual_reps is not None or self.actual_seconds is not None

    @property
    def target_met(self) -> bool:
        if self.target_reps is not None:
            return self.actual_reps is not None and self.actual_reps >= self.target_reps
        if self.target_seconds is not None:
            return self.actual_seconds is not None and self.actual_seconds >= self.target_seconds
        return self.done


@dataclass(frozen=True)
class WorkoutSummary:
    sets_planned: int
    sets_done: int
    targets_met: int
    total_reps: int
    total_seconds: int
    exercises_skipped: int
    completion_pct: int = field(default=0)


def summarize(sets: Sequence[LoggedSet]) -> WorkoutSummary:
    by_exercise: dict[str, list[LoggedSet]] = {}
    for s in sets:
        by_exercise.setdefault(s.exercise_code, []).append(s)
    done = [s for s in sets if s.done]
    planned = len(sets)
    return WorkoutSummary(
        sets_planned=planned,
        sets_done=len(done),
        targets_met=sum(1 for s in sets if s.target_met),
        total_reps=sum(s.actual_reps or 0 for s in done),
        total_seconds=sum(s.actual_seconds or 0 for s in done),
        exercises_skipped=sum(1 for v in by_exercise.values() if not any(s.done for s in v)),
        completion_pct=round(100 * len(done) / planned) if planned else 0,
    )
