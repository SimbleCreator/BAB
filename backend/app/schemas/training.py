from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.engines.training_engine import ExerciseType, Group


class ExerciseOut(BaseModel):
    code: str
    name: str
    group: Group
    difficulty: int = Field(ge=1, le=5)
    type: ExerciseType
    needs_bar: bool
    easier: str | None
    harder: str | None
    instructions: str


class DrillOut(BaseModel):
    code: str
    name: str
    seconds: int
    instructions: str


class PrescriptionOut(BaseModel):
    code: str
    name: str
    group: Group
    type: ExerciseType
    sets: int
    rest_s: int
    reps_min: int | None
    reps_max: int | None
    target_reps: int | None
    seconds_min: int | None
    seconds_max: int | None
    target_seconds: int | None


class PlannedSessionOut(BaseModel):
    day: date
    kind: str
    title: str
    focus: list[Group]
    warmup: list[DrillOut]
    exercises: list[PrescriptionOut]
    finisher: PrescriptionOut | None = Field(description="Cardio finisher for fat-loss plans")
    cooldown: list[DrillOut]
    est_minutes: int


DayStatus = Literal["rest", "planned", "not_logged", "done", "skipped"]


class PlanDayOut(BaseModel):
    day: date
    status: DayStatus = Field(
        description="rest; planned (today or later); not_logged (past, nothing saved); "
        "done; skipped"
    )
    session: PlannedSessionOut | None


class WeekOut(BaseModel):
    week_start: date = Field(description="Monday of the week")
    today: date
    split: str
    note: str | None = Field(default=None, description="Why the plan last changed, if it did")
    days: list[PlanDayOut] = Field(description="Seven days, Monday first")


class SetIn(BaseModel):
    exercise_code: str = Field(max_length=40)
    set_no: int = Field(ge=1, le=20)
    actual_reps: int | None = Field(default=None, ge=0, le=1000)
    actual_seconds: int | None = Field(default=None, ge=0, le=3600)


class WorkoutIn(BaseModel):
    """Send only what was done. Targets come from the plan. Sets left out count as not done."""

    status: Literal["done", "skipped"]
    sets: list[SetIn] = Field(default_factory=list, max_length=200)


class SetOut(BaseModel):
    exercise_code: str
    set_no: int
    target_reps: int | None
    actual_reps: int | None
    target_seconds: int | None
    actual_seconds: int | None
    target_met: bool


class WorkoutSummaryOut(BaseModel):
    sets_planned: int
    sets_done: int
    targets_met: int
    total_reps: int
    total_seconds: int
    exercises_skipped: int
    completion_pct: int


class WorkoutOut(BaseModel):
    day: date
    status: Literal["done", "skipped"]
    finished_at: datetime | None
    sets: list[SetOut]
    summary: WorkoutSummaryOut


class WorkoutBrief(BaseModel):
    day: date
    title: str
    exercise_count: int
    est_minutes: int
    status: DayStatus
