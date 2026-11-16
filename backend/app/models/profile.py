from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String(60))
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(10))
    height_cm: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    goal: Mapped[str] = mapped_column(String(20))
    level: Mapped[str] = mapped_column(String(20))
    minutes_per_day: Mapped[int] = mapped_column(Integer)
    days_per_week: Mapped[int] = mapped_column(Integer)
    has_pullup_bar: Mapped[bool] = mapped_column(Boolean)
    diet_type: Mapped[str] = mapped_column(String(10))
    daily_step_goal: Mapped[int] = mapped_column(Integer)
    timezone: Mapped[str] = mapped_column(String(64))
    training_mode: Mapped[str] = mapped_column(
        String(10), default="activity", server_default="activity"
    )
    # "Know me" (all optional; asked during onboarding or later on the profile page).
    city: Mapped[str | None] = mapped_column(String(60))
    state: Mapped[str | None] = mapped_column(String(3))
    work_type: Mapped[str | None] = mapped_column(String(10))
    food_source: Mapped[str | None] = mapped_column(String(10))
    wake_time: Mapped[str | None] = mapped_column(String(5))
    usual_foods: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    sleep_hours: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    sweet_drinks_per_day: Mapped[int | None] = mapped_column(Integer)
    fasting_note: Mapped[str | None] = mapped_column(String(80))
    food_budget_inr: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
