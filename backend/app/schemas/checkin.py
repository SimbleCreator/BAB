from datetime import date

from pydantic import BaseModel, Field, field_validator

MIN_CM, MAX_CM = 20, 250


def _cm(description: str):
    return Field(default=None, ge=MIN_CM, le=MAX_CM, description=description)


class CheckinIn(BaseModel):
    weight_kg: float = Field(ge=30, le=300)
    waist_cm: float | None = _cm("Waist, centimetres")
    chest_cm: float | None = _cm("Chest, centimetres")
    arms_cm: float | None = _cm("Upper arm, centimetres")
    thighs_cm: float | None = _cm("Thigh, centimetres")
    note: str | None = Field(default=None, max_length=500)

    @field_validator("weight_kg", "waist_cm", "chest_cm", "arms_cm", "thighs_cm")
    @classmethod
    def _one_decimal(cls, v: float | None) -> float | None:
        return None if v is None else round(v, 1)

    @field_validator("note")
    @classmethod
    def _note(cls, v: str | None) -> str | None:
        v = v.strip() if v else None
        return v or None


class CheckinOut(BaseModel):
    day: date
    weight_kg: float
    waist_cm: float | None
    chest_cm: float | None
    arms_cm: float | None
    thighs_cm: float | None
    note: str | None
    weight_change_kg: float | None = Field(description="Change from the previous check-in")
    waist_change_cm: float | None


class CheckinStatusOut(BaseModel):
    due: bool = Field(description="True when there is no check-in in the last 7 days")
    last_day: date | None
    days_since: int | None
    today: date
