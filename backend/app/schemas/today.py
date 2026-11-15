from datetime import date

from pydantic import BaseModel, Field

from app.schemas.activity import ActivityOut


class TodayOut(BaseModel):
    """Everything for the "what do I do today" screen. Sections grow with each milestone."""

    day: date = Field(description="The user's local date")
    name: str
    line: str = Field(description="Motivational line of the day")
    step_goal: int
    current_streak: int
    activity: ActivityOut | None = Field(description="Null when nothing is logged yet today")
