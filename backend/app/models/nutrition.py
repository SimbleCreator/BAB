from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class NutritionTarget(Base):
    """Daily targets from effective_from onward, until a newer row takes over."""

    __tablename__ = "nutrition_targets"
    __table_args__ = (Index("ix_nutrition_targets_user_from", "user_id", "effective_from"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    effective_from: Mapped[date] = mapped_column(Date)
    calories_kcal: Mapped[int] = mapped_column(Integer)
    protein_g: Mapped[int] = mapped_column(Integer)
    carbs_g: Mapped[int] = mapped_column(Integer)
    fat_g: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(300))


class CustomFood(Base):
    __tablename__ = "custom_foods"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    serving_label: Mapped[str] = mapped_column(String(40))
    calories_kcal: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    protein_g: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    carbs_g: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    fat_g: Mapped[Decimal] = mapped_column(Numeric(6, 1))


class Meal(Base):
    """One per user, day and meal type; items are added to it."""

    __tablename__ = "meals"
    __table_args__ = (UniqueConstraint("user_id", "day", "meal_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    meal_type: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["MealItem"]] = relationship(
        back_populates="meal",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="MealItem.id",
    )


class MealItem(Base):
    """Nutrients are stored as eaten, so later edits to a food do not change past days."""

    __tablename__ = "meal_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    meal_id: Mapped[int] = mapped_column(ForeignKey("meals.id", ondelete="CASCADE"), index=True)
    food_code: Mapped[str | None] = mapped_column(String(40))
    custom_food_id: Mapped[int | None] = mapped_column(
        ForeignKey("custom_foods.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(80))
    serving_label: Mapped[str] = mapped_column(String(40))
    servings: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    calories_kcal: Mapped[int] = mapped_column(Integer)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    carbs_g: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    fat_g: Mapped[Decimal] = mapped_column(Numeric(6, 1))

    meal: Mapped[Meal] = relationship(back_populates="items")
