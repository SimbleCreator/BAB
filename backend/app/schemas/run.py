from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import Source

MIN_DISTANCE_M, MAX_DISTANCE_M = 10, 300_000
MIN_DURATION_S, MAX_DURATION_S = 30, 48 * 3600


def _clean_note(v: str | None) -> str | None:
    v = v.strip() if v else None
    return v or None


class RunIn(BaseModel):
    day: date
    distance_m: int = Field(ge=MIN_DISTANCE_M, le=MAX_DISTANCE_M, description="Metres")
    duration_s: int = Field(ge=MIN_DURATION_S, le=MAX_DURATION_S, description="Seconds")
    note: str | None = Field(default=None, max_length=500)

    _note = field_validator("note")(_clean_note)


class RunPatch(BaseModel):
    """Only the fields sent are changed. Send note: null to clear it."""

    day: date | None = None
    distance_m: int | None = Field(default=None, ge=MIN_DISTANCE_M, le=MAX_DISTANCE_M)
    duration_s: int | None = Field(default=None, ge=MIN_DURATION_S, le=MAX_DURATION_S)
    note: str | None = Field(default=None, max_length=500)

    _note = field_validator("note")(_clean_note)


class RunOut(BaseModel):
    id: int
    day: date
    started_at: datetime | None
    distance_m: int
    duration_s: int
    pace_s_per_km: int | None = Field(description="Seconds per km")
    calories_kcal: int
    calories_estimated: Literal[True] = Field(
        default=True, description="Run calories are always an estimate"
    )
    source: Source
    note: str | None
    has_track: bool
    created_at: datetime


class SplitOut(BaseModel):
    km: int
    distance_m: int
    duration_s: int
    pace_s_per_km: int


class TrackPointOut(BaseModel):
    lat: float
    lng: float
    ele_m: float | None


class RunDetailOut(RunOut):
    splits: list[SplitOut]
    track: list[TrackPointOut] = Field(description="Empty for runs added by hand")


class RunListOut(BaseModel):
    items: list[RunOut] = Field(description="Newest first")
    total: int
